# app/services/form_service.py

from datetime import datetime
from app.models.answers_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.form_answer import FormAnswer
from app.models.form_submission import FormSubmission
from app.models.question import Question
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
        
    @staticmethod
    def get_all_forms(is_public=None):
        """
        Get all forms with optional public filter
        
        Args:
            is_public (bool, optional): Filter by public status
            
        Returns:
            list: List of Form objects
        """
        query = Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type),
        )
        
        if is_public is not None:
            query = query.filter_by(is_public=is_public)
            
        return query.order_by(Form.created_at.desc()).all()
    
    @staticmethod
    def get_form(form_id):
        """Get non-deleted form with relationships"""
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type)
        ).filter_by(id=form_id, is_deleted=False).first()

    def get_form_with_relations(self, form_id):
        """Get form with all related data loaded"""
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions).joinedload(FormQuestion.question)
        ).get(form_id)

    @staticmethod
    def get_forms_by_environment(environment_id):
        """Get non-deleted forms for an environment"""
        return (Form.query
                .join(Form.creator)
                .filter(Form.is_deleted == False)
                .filter_by(environment_id=environment_id)
                .options(
                    joinedload(Form.creator).joinedload(User.environment),
                    joinedload(Form.form_questions)
                )
                .order_by(Form.created_at.desc())
                .all())

    @staticmethod
    def get_form_submissions_count(form_id: int) -> int:
        """Get number of submissions for a form"""
        try:
            from app.models.form_submission import FormSubmission
            return FormSubmission.query.filter_by(
                form_submitted=str(form_id)
            ).count()
        except Exception as e:
            logger.error(f"Error getting submissions count: {str(e)}")
            return 0

    def get_forms_by_user_or_public(self, user_id, is_public=None):
        """Get forms created by user or public forms"""
        query = Form.query.filter(
            db.or_(
                Form.user_id == user_id,
                Form.is_public == True
            )
        )
        
        if is_public is not None:
            query = query.filter_by(is_public=is_public)
            
        return query.order_by(Form.created_at.desc()).all()
    
    @staticmethod
    def get_public_forms():
        """Get non-deleted public forms"""
        return (Form.query
                .filter_by(is_public=True, is_deleted=False)
                .options(
                    joinedload(Form.creator).joinedload(User.environment),
                    joinedload(Form.form_questions)
                        .joinedload(FormQuestion.question)
                        .joinedload(Question.question_type)
                )
                .order_by(Form.created_at.desc())
                .all())
    
    @staticmethod
    def get_forms_by_creator(username: str):
        """
        Get all forms created by a specific user
        
        Args:
            username (str): Username of the creator
            
        Returns:
            list: List of Form objects or None if user not found
        """
        try:
            from app.models.user import User  # Import here to avoid circular imports
            
            # First verify user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                return None
                
            return (Form.query
                    .filter_by(user_id=user.id)
                    .options(
                        joinedload(Form.creator).joinedload(User.environment),
                        joinedload(Form.form_questions)
                            .joinedload(FormQuestion.question)
                            .joinedload(Question.question_type)
                    )
                    .order_by(Form.created_at.desc())
                    .all())

        except Exception as e:
            logger.error(f"Error getting forms by creator: {str(e)}")
            raise

    def create_form(title, description, user_id, is_public=False):
        """Create a new form with questions"""
        try:
            form = Form(
                title=title,
                description=description,
                user_id=user_id,
                is_public=is_public
            )
            db.session.add(form)
            
            db.session.commit()
            return form, None
        except IntegrityError:
            db.session.rollback()
            return None, "Invalid user_id or question_id provided"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    @staticmethod
    def update_form(form_id, **kwargs):
        """
        Update a form's details
        
        Args:
            form_id (int): ID of the form to update
            **kwargs: Fields to update (title, description, is_public, user_id)
                
        Returns:
            tuple: (Updated Form object, error message or None)
        """
        try:
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"
                
            for key, value in kwargs.items():
                if hasattr(form, key):
                    setattr(form, key, value)
            
            form.updated_at = datetime.utcnow()
            db.session.commit()
            return form, None
            
        except IntegrityError:
            db.session.rollback()
            return None, "Database integrity error. Please check if the user_id is valid."
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    def add_questions_to_form(self, form_id, questions):
        """
        Add new questions to an existing form
        
        Args:
            form_id (int): ID of the form
            questions (list): List of question dictionaries with question_id and order_number
            
        Returns:
            tuple: (Form object, error message)
        """
        try:
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"
                
            # Get current max order number
            max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                .filter_by(form_id=form_id).scalar() or 0
                
            # Add new questions
            for i, question in enumerate(questions, start=1):
                form_question = FormQuestion(
                    form_id=form_id,
                    question_id=question['question_id'],
                    order_number=question.get('order_number', max_order + i)
                )
                db.session.add(form_question)
                
            db.session.commit()
            return form, None
        except IntegrityError:
            db.session.rollback()
            return None, "Invalid question_id provided"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    def reorder_questions(self, form_id, question_order):
        """
        Reorder questions in a form
        
        Args:
            form_id (int): ID of the form
            question_order (list): List of tuples (form_question_id, new_order)
            
        Returns:
            tuple: (Form object, error message)
        """
        try:
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"
                
            # Update order numbers
            for form_question_id, new_order in question_order:
                form_question = FormQuestion.query.get(form_question_id)
                if form_question and form_question.form_id == form_id:
                    form_question.order_number = new_order
                
            db.session.commit()
            return form, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    def submit_form(self, form_id, username, answers, attachments=None):
        """
        Submit a form with answers and optional attachments
        
        Args:
            form_id (int): ID of the form
            username (str): Username of the submitter
            answers (list): List of answer dictionaries
            attachments (list, optional): List of attachment dictionaries
            
        Returns:
            tuple: (FormSubmission object, error message)
        """
        try:
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"
                
            # Create submission
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()
            
            # Process answers
            for answer_data in answers:
                # Get the form question
                form_question = FormQuestion.query.filter_by(
                    form_id=form_id,
                    question_id=answer_data['question_id']
                ).first()
                
                if not form_question:
                    db.session.rollback()
                    return None, f"Invalid question_id: {answer_data['question_id']}"
                
                # Create form answer
                form_answer = FormAnswer(
                    form_question_id=form_question.id,
                    answer_id=answer_data['answer_id'],
                    remarks=answer_data.get('remarks')
                )
                db.session.add(form_answer)
                db.session.flush()
                
                # Link answer to submission
                answer_submitted = AnswerSubmitted(
                    form_answer_id=form_answer.id,
                    form_submission_id=submission.id
                )
                db.session.add(answer_submitted)
            
            # Process attachments if any
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment(
                        form_submission_id=submission.id,
                        file_type=attachment_data['file_type'],
                        file_path=attachment_data['file_path'],
                        file_name=attachment_data['file_name'],
                        file_size=attachment_data['file_size'],
                        is_signature=attachment_data.get('is_signature', False)
                    )
                    db.session.add(attachment)
            
            db.session.commit()
            return submission, None
            
        except IntegrityError:
            db.session.rollback()
            return None, "Database integrity error"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    def get_form_submissions(self, form_id):
        """
        Get all submissions for a form
        
        Args:
            form_id (int): ID of the form
            
        Returns:
            list: List of FormSubmission objects
        """
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
        
    def get_form_statistics(self, form_id):
        """
        Get statistics for a form
        
        Args:
            form_id (int): ID of the form
            
        Returns:
            dict: Statistics dictionary containing counts and temporal data
        """
        try:
            form = Form.query.get(form_id)
            if not form:
                return None
                
            submissions = form.submissions
            total_submissions = len(submissions)
            
            # Initialize statistics
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
                # Calculate submission trends
                for submission in submissions:
                    date = submission.submitted_at.date()
                    week = submission.submitted_at.isocalendar()[1]
                    month = submission.submitted_at.strftime('%Y-%m')
                    
                    # Daily stats
                    stats['submissions_by_date'][str(date)] = \
                        stats['submissions_by_date'].get(str(date), 0) + 1
                        
                    # Weekly stats
                    stats['submission_trends']['weekly'][str(week)] = \
                        stats['submission_trends']['weekly'].get(str(week), 0) + 1
                        
                    # Monthly stats
                    stats['submission_trends']['monthly'][month] = \
                        stats['submission_trends']['monthly'].get(month, 0) + 1
                
                # Calculate question statistics
                for form_question in form.form_questions:
                    question_id = form_question.question_id
                    answers = FormAnswer.query\
                        .join(AnswerSubmitted)\
                        .filter(FormAnswer.form_question_id == form_question.id)\
                        .all()
                        
                    stats['questions_stats'][question_id] = {
                        'total_answers': len(answers),
                        'has_remarks': len([a for a in answers if a.remarks]),
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting form statistics: {str(e)}")
            return None
        
    @staticmethod
    def search_forms(query=None, user_id=None, is_public=None):
        """Search non-deleted forms"""
        search_query = Form.query.filter_by(is_deleted=False)
        
        if query:
            search_query = search_query.filter(
                db.or_(
                    Form.title.ilike(f'%{query}%'),
                    Form.description.ilike(f'%{query}%')
                )
            )
        if user_id is not None:
            search_query = search_query.filter_by(user_id=user_id)
        if is_public is not None:
            search_query = search_query.filter_by(is_public=is_public)
            
        return search_query.order_by(Form.created_at.desc()).all()
    
    def delete_form(form_id):
        """
        Delete a form and all its related data
        
        Args:
            form_id (int): ID of the form to delete
            
        Returns:
            tuple: (bool success, str error_message)
        """
        try:
            form = Form.query.get(form_id)
            form_question = FormQuestion.query.filter_by(form_id=form_id).first()
            if not form:
                return False, "Form not found"
            
            if FormQuestion.query.filter_by(form_id=form_id).first():
                FormQuestion.query.filter_by(form_id=form_id).delete()
            if form_question:
                FormAnswer.query.filter_by(form_question_id=form_question.id).delete()
                        
            # Delete the form itself
            form.soft_delete()
            db.session.commit()
            
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)