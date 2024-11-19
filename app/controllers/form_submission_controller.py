from app.models.answer import Answer
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.services.form_submission_service import FormSubmissionService
from datetime import datetime
import logging

from app.utils.permission_manager import RoleType

logger = logging.getLogger(__name__)

class FormSubmissionController:
    @staticmethod
    def validate_submission_data(form_id: int, answers: list) -> tuple[bool, str]:
        """Validate submission data before processing"""
        try:
            # Validate form exists and is active
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return False, "Form not found or inactive"
            
            # Get all valid form questions
            form_questions = FormQuestion.query.filter_by(
                form_id=form_id,
                is_deleted=False
            ).all()
            if not form_questions:
                return False, "Form has no active questions"
                
            form_question_ids = {fq.id for fq in form_questions}
            
            # Validate answers
            for answer in answers:
                if answer['form_question_id'] not in form_question_ids:
                    return False, f"Invalid form question ID: {answer['form_question_id']}"
                
                # Validate answer exists
                answer_exists = Answer.query.filter_by(
                    id=answer['answer_id'],
                    is_deleted=False
                ).first()
                if not answer_exists:
                    return False, f"Invalid answer ID: {answer['answer_id']}"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating submission data: {str(e)}")
            return False, str(e)
        
    @staticmethod
    def create_submission(form_id: int, username: str) -> tuple:
        """
        Create a new form submission
        
        Args:
            form_id (int): ID of the form being submitted
            username (str): Username of the submitter
            answers (list): List of answer IDs
            attachments (list, optional): List of attachment data
            
        Returns:
            tuple: (FormSubmission object, error message)
        """
        try:
            # Validate form exists
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"

            # Create submission via service
            return FormSubmissionService.create_submission(
                form_id=form_id,
                username=username
            )

        except Exception as e:
            logger.error(f"Controller error creating submission: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_all_submissions(user, filters: dict = None) -> list:
        """
        Get all submissions based on user role and filters
        
        Args:
            user: Current user object
            filters (dict): Optional filters
            
        Returns:
            list: List of FormSubmission objects
        """
        try:
            # Initialize filters if None
            filters = filters or {}
            
            # Apply role-based filtering
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Add environment filter for managers and supervisors
                    filters['environment_id'] = user.environment_id
                else:
                    # Regular users can only see their submissions
                    filters['submitted_by'] = user.username
                    
            return FormSubmissionService.get_all_submissions(filters)
            
        except Exception as e:
            logger.error(f"Error getting submissions in controller: {str(e)}")
            return []

    @staticmethod
    def get_submission(submission_id: int) -> tuple:
        """
        Get a specific submission
        
        Args:
            submission_id (int): ID of the form submission
            
        Returns:
            tuple: (FormSubmission object, error message)
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, "Form submission not found"
            return submission, None
        except Exception as e:
            logger.error(f"Error getting submission {submission_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_submissions_by_form(form_id: int):
        """Get all submissions for a form"""
        try:
            return FormSubmission.query.filter_by(
                form_id=form_id,
                is_deleted=False
            ).order_by(FormSubmission.submitted_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting form submissions: {str(e)}")
            return None

    @staticmethod
    def get_submissions_by_user(username, form_id=None, start_date=None, end_date=None):
        """Get submissions by username with optional filters"""
        return FormSubmissionService.get_submissions_by_user(
            username, form_id, start_date, end_date
        )

    @staticmethod
    def get_submissions_by_environment(environment_id, form_id=None):
        """Get submissions for a specific environment"""
        return FormSubmissionService.get_submissions_by_environment(
            environment_id, form_id
        )

    @staticmethod
    def update_submission(submission_id, answers_data=None, attachments_data=None):
        """Update a submission"""
        return FormSubmissionService.update_submission(
            submission_id, answers_data, attachments_data
        )

    @staticmethod
    def delete_submission(submission_id):
        """Delete a submission"""
        return FormSubmissionService.delete_submission(submission_id)

    @staticmethod
    def get_submission_statistics(form_id=None, environment_id=None, date_range=None):
        """Get submission statistics"""
        return FormSubmissionService.get_submission_statistics(
            form_id, environment_id, date_range
        )