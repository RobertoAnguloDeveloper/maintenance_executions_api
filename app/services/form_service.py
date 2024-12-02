from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from app.models.answers_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.form_answer import FormAnswer
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.models.question_type import QuestionType
from app.models.user import User
from app.services.base_service import BaseService
from app.models.form import Form
from app.models.form_question import FormQuestion
from app import db
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

class FormService(BaseService):
    def __init__(self):
        super().__init__(Form)

    @classmethod
    def _get_base_query(cls):
        """Base query with common joins and filters"""
        return (Form.query
            .options(
                joinedload(Form.creator),
                joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type)
            )
            .filter_by(is_deleted=False))

    @classmethod
    def _handle_transaction(cls, operation: callable, *args, **kwargs) -> Tuple[Optional[Any], Optional[str]]:
        """Generic transaction handler"""
        try:
            with db.session.begin_nested():
                result = operation(*args, **kwargs)
                db.session.commit()
                return result, None
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Database integrity error: {str(e)}")
            return None, "Database integrity error"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Operation error: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_forms(is_public=None):
        """Get all forms with optional public filter"""
        query = Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type),
        ).filter_by(is_deleted=False)

        if is_public is not None:
            query = query.filter_by(is_public=is_public)
            
        return query.order_by(Form.created_at.desc()).all()

    @staticmethod
    def get_form(form_id: int) -> Optional[Form]:
        """Get non-deleted form with relationships"""
        try:
            return Form.query.options(
                joinedload(Form.creator),
                joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type)
            ).filter_by(
                id=form_id,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error getting form {form_id}: {str(e)}")
            raise

    def get_form_with_relations(self, form_id):
        """Get form with all related data loaded"""
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions).joinedload(FormQuestion.question)
        ).filter_by(id=form_id, is_default=False).first()

    @staticmethod
    def get_forms_by_environment(environment_id: int) -> list[Form]:
        """Get non-deleted forms for an environment"""
        return (Form.query
            .join(Form.creator)
            .filter(
                Form.is_deleted == False,
                User.environment_id == environment_id,
                User.is_deleted == False
            )
            .options(
                joinedload(Form.creator).joinedload(User.environment),
                joinedload(Form.form_questions)
            ).filter_by(is_deleted=False)
            .order_by(Form.created_at.desc())
            .all())

    @staticmethod
    def get_form_submissions_count(form_id: int) -> int:
        """Get number of submissions for a form"""
        try:
            return FormSubmission.query.filter_by(
                form_submitted=str(form_id)
            ).count()
        except Exception as e:
            logger.error(f"Error getting submissions count: {str(e)}")
            return 0

    @staticmethod
    def get_forms_by_user_or_public(
        user_id: int,
        is_public: Optional[bool] = None
    ) -> list[Form]:
        """Get forms created by user or public forms"""
        query = Form.query.filter(
            db.or_(
                Form.user_id == user_id,
                Form.is_public == True
            ),
            Form.is_deleted == False
        )
        
        if is_public is not None:
            query = query.filter(Form.is_public == is_public)
            
        return query.order_by(Form.created_at.desc()).all()

    @staticmethod
    def get_public_forms() -> list[Form]:
        """Get non-deleted public forms"""
        return (Form.query
            .filter_by(
                is_public=True,
                is_deleted=False
            )
            .options(
                joinedload(Form.creator).joinedload(User.environment),
                joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type)
            )
            .order_by(Form.created_at.desc())
            .all())

    @staticmethod
    def get_forms_by_creator(username: str) -> Optional[List[Form]]:
        """Get all forms created by a specific user"""
        try:
            user = User.query.filter_by(
                username=username,
                is_deleted=False
            ).first()
            
            if not user:
                return None
                
            return (Form.query
                    .filter_by(
                        user_id=user.id,
                        is_deleted=False
                    )
                    .join(User, User.id == Form.user_id)
                    .options(
                        joinedload(Form.creator)
                            .joinedload(User.environment),
                        joinedload(Form.form_questions)
                            .filter(FormQuestion.is_deleted == False)
                            .joinedload(FormQuestion.question)
                            .filter(Question.is_deleted == False)
                            .joinedload(Question.question_type)
                            .filter(QuestionType.is_deleted == False)
                    )
                    .filter(User.is_deleted == False)
                    .order_by(Form.created_at.desc())
                    .all())
        except Exception as e:
            logger.error(f"Error getting forms by creator: {str(e)}")
            raise

    @classmethod
    def create_form(cls, title: str, description: str, user_id: int, is_public: bool = False) -> Tuple[Optional[Form], Optional[str]]:
        """Create a new form"""
        def _create():
            form = Form(
                title=title,
                description=description,
                user_id=user_id,
                is_public=is_public
            )
            db.session.add(form)
            return form

        return cls._handle_transaction(_create)

    @classmethod
    def update_form(cls, form_id: int, **kwargs) -> Tuple[Optional[Form], Optional[str]]:
        """Update a form's details"""
        def _update():
            form = Form.query.get(form_id)
            if not form:
                raise ValueError("Form not found")
                
            for key, value in kwargs.items():
                if hasattr(form, key):
                    setattr(form, key, value)
            
            form.updated_at = datetime.utcnow()
            return form

        return cls._handle_transaction(_update)

    @classmethod
    def add_questions_to_form(cls, form_id: int, questions: List[Dict]) -> Tuple[Optional[Form], Optional[str]]:
        """Add new questions to an existing form"""
        def _add_questions():
            form = Form.query.get(form_id)
            if not form:
                raise ValueError("Form not found")

            max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                .filter_by(form_id=form_id).scalar() or 0

            for i, question in enumerate(questions, start=1):
                form_question = FormQuestion(
                    form_id=form_id,
                    question_id=question['question_id'],
                    order_number=question.get('order_number', max_order + i)
                )
                db.session.add(form_question)

            return form

        return cls._handle_transaction(_add_questions)

    @classmethod
    def reorder_questions(cls, form_id: int, question_order: List[Tuple[int, int]]) -> Tuple[Optional[Form], Optional[str]]:
        """Reorder questions in a form"""
        def _reorder():
            form = Form.query.get(form_id)
            if not form:
                raise ValueError("Form not found")

            for form_question_id, new_order in question_order:
                form_question = FormQuestion.query.get(form_question_id)
                if form_question and form_question.form_id == form_id:
                    form_question.order_number = new_order

            return form

        return cls._handle_transaction(_reorder)

    @classmethod
    def submit_form(cls, form_id: int, username: str, answers: List[Dict]) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """Submit form with answers"""
        def _submit():
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()

            for answer_data in answers:
                form_answer = FormAnswer.query.get(answer_data['form_answer_id'])
                if not form_answer:
                    raise ValueError(f"Invalid form answer ID: {answer_data['form_answer_id']}")

                answer_submitted = AnswerSubmitted(
                    form_answers_id=form_answer.id,
                    form_submissions_id=submission.id,
                    text_answered=answer_data.get('text_answered') if form_answer.requires_text_answer() else None
                )
                db.session.add(answer_submitted)

            return submission

        return cls._handle_transaction(_submit)

    @staticmethod
    def get_form_submissions(form_id: int) -> List[FormSubmission]:
        """Get all submissions for a form"""
        return (FormSubmission.query
                .filter_by(form_id=form_id)
                .options(
                    joinedload(FormSubmission.answers_submitted)
                        .joinedload(AnswerSubmitted.form_answer)
                        .joinedload(FormAnswer.form_question)
                        .joinedload(FormQuestion.question),
                    joinedload(FormSubmission.attachments)
                )
                .order_by(FormSubmission.submitted_at.desc())
                .all())

    @classmethod
    def get_form_statistics(cls, form_id: int) -> Optional[Dict]:
        """Get statistics for a form"""
        try:
            form = Form.query.filter_by(
                id=form_id,
                is_deleted=False
            ).first()
            
            if not form:
                return None
                
            submissions = [s for s in form.submissions if not s.is_deleted]
            total_submissions = len(submissions)
            
            stats = {
                'total_submissions': total_submissions,
                'submissions_by_date': {},
                'questions_stats': {},
                'average_completion_time': None,
                'submission_trends': {
                    'daily': {},
                    'weekly': {},
                    'monthly': {}
                }
            }

            if total_submissions > 0:
                stats.update(cls._calculate_submission_trends(submissions))
                stats.update(cls._calculate_question_statistics(form))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting form statistics: {str(e)}")
            return None

    @staticmethod
    def _calculate_submission_trends(submissions: List[FormSubmission]) -> Dict:
        """Calculate submission trends"""
        trends = {
            'submissions_by_date': {},
            'submission_trends': {
                'daily': {},
                'weekly': {},
                'monthly': {}
            }
        }
        
        for submission in submissions:
            date = submission.submitted_at.date()
            week = submission.submitted_at.isocalendar()[1]
            month = submission.submitted_at.strftime('%Y-%m')
            
            trends['submissions_by_date'][str(date)] = \
                trends['submissions_by_date'].get(str(date), 0) + 1
            trends['submission_trends']['weekly'][str(week)] = \
                trends['submission_trends']['weekly'].get(str(week), 0) + 1
            trends['submission_trends']['monthly'][month] = \
                trends['submission_trends']['monthly'].get(month, 0) + 1
                
        return trends

    @staticmethod
    def _calculate_question_statistics(form: Form) -> Dict:
        """Calculate question statistics"""
        stats = {'questions_stats': {}}
        
        for form_question in form.form_questions:
            if form_question.is_deleted:
                continue
                
            answers = (FormAnswer.query
                .join(AnswerSubmitted)
                .filter(
                    FormAnswer.form_question_id == form_question.id,
                    FormAnswer.is_deleted == False
                ).all())

            stats['questions_stats'][form_question.question_id] = {
                'total_answers': len(answers),
                'remarks': len([a for a in answers if a.remarks])
            }
            
        return stats

    @classmethod
    def delete_form(cls, form_id: int) -> Tuple[bool, Union[Dict, str]]:
        """Delete form and related data"""
        try:
            # Get the form with is_deleted=False check
            form = cls.get_form(form_id)
            if not form:
                return False, "Form not found"

            # Perform cascading soft delete
            deletion_stats = cls._perform_cascading_delete(form)
            
            # Finally soft delete the form itself
            form.soft_delete()
            db.session.commit()
            
            logger.info(f"Form {form_id} and associated data deleted successfully")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting form: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def _perform_cascading_delete(form: Form) -> Dict:
        """Perform cascading soft delete of form-related data"""
        stats = {
            'form_questions': 0,
            'form_answers': 0,
            'form_submissions': 0,
            'answers_submitted': 0,
            'attachments': 0
        }

        # Soft delete form questions and related data
        for form_question in FormQuestion.query.filter_by(
            form_id=form.id,
            is_deleted=False
        ).all():
            form_question.soft_delete()
            stats['form_questions'] += 1

            # Soft delete form answers
            for form_answer in FormAnswer.query.filter_by(
                form_question_id=form_question.id,
                is_deleted=False
            ).all():
                form_answer.soft_delete()
                stats['form_answers'] += 1

        # Soft delete submissions and related data
        for submission in FormSubmission.query.filter_by(
            form_id=form.id,
            is_deleted=False
            ).all():
            submission.soft_delete()
            stats['form_submissions'] += 1

            # Soft delete attachments
            for attachment in Attachment.query.filter_by(
                form_submission_id=submission.id,
                is_deleted=False
            ).all():
                attachment.soft_delete()
                stats['attachments'] += 1

            # Soft delete submitted answers
            submitted_answers = (AnswerSubmitted.query
                .join(FormAnswer)
                .join(FormQuestion)
                .filter(
                    FormQuestion.form_id == form.id,
                    AnswerSubmitted.is_deleted == False
                ).all())

            for submitted in submitted_answers:
                submitted.soft_delete()
                stats['answers_submitted'] += 1

        return stats

    @staticmethod
    def search_forms(
        search_text: Optional[str] = None,
        user_id: Optional[int] = None,
        is_public: Optional[bool] = None
    ) -> List[Form]:
        """
        Search forms with filters
        
        Args:
            search_text: Optional text to search in title and description
            user_id: Optional user ID to filter by creator
            is_public: Optional filter for public forms
            
        Returns:
            List of matching Form objects
        """
        query = Form.query.filter_by(is_deleted=False)
        
        if search_text:
            query = query.filter(
                db.or_(
                    Form.title.ilike(f'%{search_text}%'),
                    Form.description.ilike(f'%{search_text}%')
                )
            )
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        if is_public is not None:
            query = query.filter_by(is_public=is_public)
            
        return query.order_by(Form.created_at.desc()).all()

    @classmethod
    def get_user_submission_statistics(cls, username: str, form_id: Optional[int] = None) -> Dict:
        """
        Get submission statistics for a specific user
        
        Args:
            username: Username to get statistics for
            form_id: Optional form ID to filter statistics
            
        Returns:
            Dictionary containing submission statistics
        """
        query = FormSubmission.query.filter_by(
            submitted_by=username,
            is_deleted=False
        )
        
        if form_id:
            query = query.filter_by(form_id=form_id)
            
        submissions = query.order_by(FormSubmission.submitted_at.desc()).all()
        
        return {
            'total_submissions': len(submissions),
            'submission_trends': cls._calculate_submission_trends(submissions)['submission_trends'],
            'latest_submission': submissions[0].submitted_at.isoformat() if submissions else None,
            'forms_submitted': len(set(s.form_id for s in submissions))
        }