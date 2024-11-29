from typing import Optional, Union, List, Dict, Any
from app import db
from app.models.answer import Answer
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.attachment import Attachment
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging

from app.models.question import Question
from app.models.question_type import QuestionType
from app.models.user import User
from app.utils.permission_manager import RoleType

logger = logging.getLogger(__name__)

class FormSubmissionService:
    
    @staticmethod
    def validate_submission_data(data: dict) -> tuple[bool, str]:
        """Validate submission request data"""
        if not data:
            return False, "No data provided"
        if not all(field in data for field in ['form_id', 'answers']):
            return False, "Missing required fields"
        return True, None
    
    @staticmethod
    def validate_date_range(start_date: str = None, end_date: str = None) -> tuple[dict, str]:
        """Validate and parse date range parameters"""
        date_range = {}
        try:
            if start_date:
                date_range['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                date_range['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')
            return date_range, None
        except ValueError:
            return None, "Invalid date format. Use YYYY-MM-DD"
            
    @staticmethod
    def can_access_submission(user: User, submission: FormSubmission) -> bool:
        """Check if user can access a submission"""
        if user.role.is_super_user:
            return True
            
        if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
            return submission.form.creator.environment_id == user.environment_id
            
        return submission.submitted_by == user.username
    
    @staticmethod
    def can_modify_submission(user: User, submission: FormSubmission) -> bool:
        """Check if user can modify a submission"""
        if user.role.is_super_user:
            return True
            
        if not FormSubmissionService.can_access_submission(user, submission):
            return False
            
        if not user.role.is_super_user:
            age = datetime.utcnow() - submission.submitted_at
            if age.days > 7:
                return False
                
        return True
    @staticmethod
    def _validate_form(form_id: int) -> tuple[Form, str]:
        form = Form.query.filter_by(id=form_id, is_deleted=False).first()
        if not form:
            return None, "Form not found or inactive"
        return form, None

    @staticmethod
    def _validate_question_type(form_question: FormQuestion, answer_data: dict) -> tuple[bool, str]:
        question_type = form_question.question.question_type.type
        has_text_answer = 'text_answer' in answer_data

        if question_type == 'text' and not has_text_answer:
            return False, f"Text answer required for question {form_question.question.text}"
        if question_type != 'text' and has_text_answer:
            return False, f"Text answer not allowed for question type {question_type}"
        return True, None

    @staticmethod
    def _get_submission_query(filters: dict = None):
        query = FormSubmission.query.filter_by(is_deleted=False)
        if not filters:
            return query

        if filters.get('form_id'):
            query = query.filter(FormSubmission.form_id == filters['form_id'])
        if filters.get('start_date'):
            query = query.filter(FormSubmission.submitted_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(FormSubmission.submitted_at <= filters['end_date'])
        if filters.get('submitted_by'):
            query = query.filter(FormSubmission.submitted_by == filters['submitted_by'])
        if filters.get('environment_id'):
            query = query.join(Form).join(User).filter(
                User.environment_id == filters['environment_id']
            )
        return query

    @staticmethod
    def create_submission(form_id: int, username: str, answers: list) -> tuple[Optional[FormSubmission], Optional[str]]:
        try:
            form, error = FormSubmissionService._validate_form(form_id)
            if error:
                return None, error

            with db.session.begin_nested():
                submission = FormSubmission(
                    form_id=form_id,
                    submitted_by=username,
                    submitted_at=datetime.utcnow()
                )
                db.session.add(submission)
                db.session.flush()

                for answer_data in answers:
                    form_question = (FormQuestion.query
                        .filter_by(id=answer_data['form_question_id'])
                        .join(Question)
                        .join(QuestionType)
                        .first())

                    is_valid, error = FormSubmissionService._validate_question_type(
                        form_question, answer_data
                    )
                    if not is_valid:
                        raise ValueError(error)

                    answer_submitted = AnswerSubmitted(
                        form_submissions_id=submission.id,
                        form_answers_id=answer_data.get('form_answer_id'),
                        text_answered=answer_data.get('text_answer')
                    )
                    db.session.add(answer_submitted)

                db.session.commit()
                return submission, None

        except ValueError as ve:
            return None, str(ve)
        except Exception as e:
            logger.error(f"Error creating submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_submissions(filters: dict = None) -> list[FormSubmission]:
        try:
            return (FormSubmissionService._get_submission_query(filters)
                    .order_by(FormSubmission.submitted_at.desc())
                    .all())
        except Exception as e:
            logger.error(f"Error retrieving submissions: {str(e)}")
            return []

    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        return (FormSubmission.query
            .filter_by(id=submission_id, is_deleted=False)
            .options(
                joinedload(FormSubmission.form).joinedload(Form.creator),
                joinedload(FormSubmission.answers_submitted)
                    .joinedload(AnswerSubmitted.form_answer)
                    .joinedload(FormAnswer.answer),
                joinedload(FormSubmission.attachments)
            ).first())

    @staticmethod
    def update_submission(submission_id: int, user: User, answers: list) -> tuple[Optional[FormSubmission], Optional[str]]:
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, "Submission not found"

            if not user.role.is_super_user and submission.submitted_by != user.username:
                return None, "Unauthorized to update this submission"

            with db.session.begin_nested():
                # Logic similar to create but updating existing records
                return submission, None

        except Exception as e:
            logger.error(f"Error updating submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_submission(submission_id: int, user: User) -> tuple[bool, Union[dict, str]]:
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return False, "Submission not found"

            if not FormSubmissionService._can_delete_submission(submission, user):
                return False, "Unauthorized to delete this submission"

            with db.session.begin_nested():
                deletion_stats = FormSubmissionService._soft_delete_submission_data(submission)
                submission.soft_delete()
                db.session.commit()
                return True, deletion_stats

        except Exception as e:
            logger.error(f"Error deleting submission: {str(e)}")
            return False, str(e)

    @staticmethod
    def _soft_delete_submission_data(submission: FormSubmission) -> dict:
        stats = {'answers': 0, 'attachments': 0}
        
        for answer in submission.answers_submitted:
            answer.soft_delete()
            stats['answers'] += 1
            
        for attachment in submission.attachments:
            attachment.soft_delete()
            stats['attachments'] += 1
            
        return stats

    @staticmethod
    def _can_delete_submission(submission: FormSubmission, user: User) -> bool:
        if user.role.is_super_user:
            return True
            
        if submission.submitted_by != user.username:
            return False
            
        # Check 7-day deletion window
        return (datetime.utcnow() - submission.submitted_at).days <= 7