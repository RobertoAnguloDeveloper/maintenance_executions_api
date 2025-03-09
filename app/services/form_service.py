from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from app.models.answer_submitted import AnswerSubmitted
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

from app.utils.permission_manager import RoleType

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
    def get_all_forms(user, is_public=None):
        """Get all forms with role-based filtering and public forms"""
        try:
            query = Form.query.options(
                joinedload(Form.creator),
                joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type),
            ).filter_by(is_deleted=False)

            # Base query for public forms
            public_forms = query.filter_by(is_public=True)

            # If user is admin, they see all forms
            if user.role.is_super_user:
                return query.order_by(Form.created_at.desc()).all()
            
            # For supervisors and site managers, see forms in their environment plus public forms
            elif user.role.name in [RoleType.SUPERVISOR, RoleType.SITE_MANAGER, RoleType.TECHNICIAN]:
                return (query.filter(
                    db.or_(
                        Form.is_public == True,
                        db.and_(
                            Form.creator.has(User.environment_id == user.environment_id)
                        )
                    )
                ).order_by(Form.created_at.desc()).all())
                
            # For technicians, see public forms only
            else:
                return public_forms.order_by(Form.created_at.desc()).all()

        except Exception as e:
            logger.error(f"Error in get_all_forms: {str(e)}")
            raise

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
        try:
            forms = (Form.query
                .join(Form.creator)
                .filter(
                    Form.is_deleted == False,
                    User.environment_id == environment_id,
                    User.is_deleted == False
                )
                .options(
                    joinedload(Form.creator).joinedload(User.environment),
                    joinedload(Form.form_questions).joinedload(FormQuestion.question)
                )
                .order_by(Form.created_at.desc())
                .all())
            return forms
        except Exception as e:
            logger.error(f"Error in get_forms_by_environment: {str(e)}")
            return []

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
    def get_public_forms() -> List[Form]:
        """Get non-deleted public forms"""
        try:
            forms = (Form.query
                .filter_by(
                    is_public=True,
                    is_deleted=False
                )
                .options(
                    joinedload(Form.creator).joinedload(User.environment),
                    joinedload(Form.form_questions).joinedload(FormQuestion.question)
                )
                .order_by(Form.created_at.desc())
                .all())
            return forms
        except Exception as e:
            logger.error(f"Error in get_public_forms: {str(e)}")
            return None

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
                    .join(User)
                    .options(
                        joinedload(Form.creator).joinedload(User.environment),
                        joinedload(Form.form_questions)
                            .joinedload(FormQuestion.question)
                            .joinedload(Question.question_type)
                    )
                    .filter(User.is_deleted == False)
                    .order_by(Form.created_at.desc())
                    .all())
        except Exception as e:
            logger.error(f"Error in get_forms_by_creator: {str(e)}")
            return None

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

    @staticmethod
    def update_form(form_id: int, **kwargs) -> Tuple[Optional[Form], Optional[str]]:
        """Update a form's details"""
        try:
            # Get form with is_deleted=False check
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found"

            # Update allowed fields
            for key, value in kwargs.items():
                if hasattr(form, key):
                    setattr(form, key, value)
            
            form.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                return form, None
            except IntegrityError as e:
                db.session.rollback()
                logger.error(f"Database integrity error: {str(e)}")
                return None, "Database integrity error"
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error committing changes: {str(e)}")
                return None, str(e)

        except Exception as e:
            logger.error(f"Error updating form: {str(e)}")
            return None, str(e)

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

    @staticmethod
    def get_form_statistics(form_id: int) -> Optional[Dict]:
        """
        Get comprehensive statistics for a form
        
        Args:
            form_id: ID of the form
            
        Returns:
            Optional[Dict]: Statistics data or None if error
        """
        try:
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None

            # Get all non-deleted submissions
            submissions = [s for s in form.submissions if not s.is_deleted]
            
            stats = {
                'total_submissions': len(submissions),
                'submission_trends': {
                    'daily': {},
                    'weekly': {},
                    'monthly': {}
                },
                'questions_stats': {},
                'completion_rate': 0
            }

            if submissions:
                # Calculate submission trends
                for submission in submissions:
                    date = submission.submitted_at.date().isoformat()
                    week = f"{submission.submitted_at.year}-W{submission.submitted_at.isocalendar()[1]}"
                    month = submission.submitted_at.strftime('%Y-%m')

                    stats['submission_trends']['daily'][date] = \
                        stats['submission_trends']['daily'].get(date, 0) + 1
                    stats['submission_trends']['weekly'][week] = \
                        stats['submission_trends']['weekly'].get(week, 0) + 1
                    stats['submission_trends']['monthly'][month] = \
                        stats['submission_trends']['monthly'].get(month, 0) + 1

                # Calculate question statistics
                total_questions = len([q for q in form.form_questions if not q.is_deleted])
                
                for form_question in form.form_questions:
                    if form_question.is_deleted:
                        continue
                        
                    answers = AnswerSubmitted.query.join(
                        FormSubmission
                    ).filter(
                        FormSubmission.form_id == form_id,
                        FormSubmission.is_deleted == False,
                        AnswerSubmitted.question == form_question.question.text
                    ).all()

                    stats['questions_stats'][form_question.question_id] = {
                        'total_answers': len(answers),
                        'question_text': form_question.question.text,
                        'question_type': form_question.question.question_type.type
                    }

                # Calculate completion rate
                if total_questions > 0:
                    completed_submissions = len([
                        s for s in submissions 
                        if len(s.answers_submitted) >= total_questions
                    ])
                    stats['completion_rate'] = (completed_submissions / len(submissions)) * 100

            return stats

        except Exception as e:
            logger.error(f"Error generating form statistics: {str(e)}")
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
        """
        Delete form while preserving related submission data.
        This soft deletes the form but keeps submissions, attachments and submitted answers accessible.
        """
        try:
            # Get the form with is_deleted=False check
            form = cls.get_form(form_id)
            if not form:
                return False, "Form not found"

            # Start transaction
            db.session.begin_nested()
            try:
                deletion_stats = {
                    'form_questions': 0,
                    'form_answers': 0
                }
                
                # Soft delete form questions and their answers only
                # NOT affecting submissions, attachments, or submitted answers
                for form_question in FormQuestion.query.filter_by(
                    form_id=form.id,
                    is_deleted=False
                ).all():
                    form_question.soft_delete()
                    deletion_stats['form_questions'] += 1

                    # Soft delete form answers (template answers, not submitted answers)
                    for form_answer in FormAnswer.query.filter_by(
                        form_question_id=form_question.id,
                        is_deleted=False
                    ).all():
                        form_answer.soft_delete()
                        deletion_stats['form_answers'] += 1

                # Soft delete the form itself only
                form.soft_delete()
                
                # Commit changes
                db.session.commit()
                
                logger.info(f"Form {form_id} deleted successfully while preserving submission data. "
                        f"Stats: {deletion_stats}")
                return True, deletion_stats
                
            except Exception as nested_exception:
                db.session.rollback()
                raise nested_exception

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