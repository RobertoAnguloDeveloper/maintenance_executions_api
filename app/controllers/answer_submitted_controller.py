from typing import Dict, List, Optional, Tuple
from app.models import user
from app.services.answer_submitted_service import AnswerSubmittedService
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedController:
    @staticmethod
    def create_answer_submitted(
        form_answer_id: int,
        form_submission_id: int,
        text_answered: Optional[str] = None,
        current_user: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a new submitted answer with validation and access control
        
        Args:
            form_answer_id: ID of the form answer
            form_submission_id: ID of the form submission
            text_answered: Optional text answer
            current_user: Username of current user for access control
            
        Returns:
            tuple: (Created answer submitted data or None, Error message or None)
        """
        try:
            # Validate submission exists and check access rights
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"

            # Only submission owner can add answers
            if current_user and submission.submitted_by != current_user:
                return None, "Unauthorized: Can only add answers to own submissions"

            # Create the answer submission
            answer_submitted, error = AnswerSubmittedService.create_answer_submitted(
                form_answer_id=form_answer_id,
                form_submission_id=form_submission_id,
                text_answered=text_answered
            )
            
            if error:
                return None, error

            return answer_submitted.to_dict() if answer_submitted else None, None

        except Exception as e:
            logger.error(f"Error in create_answer_submitted controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_answers_submitted(
        user,
        filters: Dict = None
    ) -> List[Dict]:
        """
        Get all answers submitted with role-based access control
        
        Args:
            user: Current user object for role-based access
            filters: Optional filters (form_id, environment_id, date range)
            
        Returns:
            list: List of answer submitted dictionaries
        """
        try:
            # Initialize filters if None
            filters = filters or {}
            
            # Apply role-based filtering
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Can only see answers in their environment
                    filters['environment_id'] = user.environment_id
                else:
                    # Regular users can only see their own submissions
                    filters['submitted_by'] = user.username

            answers = AnswerSubmittedService.get_all_answers_submitted(filters)
            return [answer.to_dict() for answer in answers if answer]

        except Exception as e:
            logger.error(f"Error getting answers submitted in controller: {str(e)}")
            return []

    @staticmethod
    def get_answer_submitted(
        answer_submitted_id: int,
        current_user: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get a specific submitted answer with access control
        """
        try:
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return None, "Answer submission not found"

            # Access control
            if current_user and user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if answer.form_submission.form.creator.environment_id != user.environment_id:
                        return None, "Unauthorized access"
                elif answer.form_submission.submitted_by != current_user:
                    return None, "Unauthorized access"

            return answer.to_dict(), None

        except Exception as e:
            logger.error(f"Error getting answer submitted {answer_submitted_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_answers_by_submission(
        submission_id: int,
        current_user: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all submitted answers for a form submission
        
        Args:
            submission_id: ID of the form submission
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (List of answer submitted dictionaries, Error message or None)
        """
        try:
            # Get submission for access control
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return [], "Form submission not found"

            # Access control
            if current_user and user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != user.environment_id:
                        return [], "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return [], "Unauthorized access"

            answers, error = AnswerSubmittedService.get_answers_by_submission(submission_id)
            if error:
                return [], error

            return [answer.to_dict() for answer in answers], None

        except Exception as e:
            logger.error(f"Error getting answers by submission in controller: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_answer_submitted(
        answer_submitted_id: int,
        text_answered: Optional[str] = None,
        current_user: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Update a submitted answer with access control
        
        Args:
            answer_submitted_id: ID of the answer submission
            text_answered: New text answer value
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (Updated answer submitted data or None, Error message or None)
        """
        try:
            # Get existing answer for access control
            current_answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not current_answer:
                return None, "Answer submission not found"

            # Access control
            if current_user and user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if current_answer.form_submission.form.creator.environment_id != user.environment_id:
                        return None, "Unauthorized access"
                elif current_answer.form_submission.submitted_by != current_user:
                    return None, "Unauthorized access"

            # Check submission age for non-admin users
            if user_role != RoleType.ADMIN:
                submission_age = datetime.utcnow() - current_answer.form_submission.submitted_at
                if submission_age.days > 7:  # Configurable timeframe
                    return None, "Cannot update answers older than 7 days"

            updated_answer, error = AnswerSubmittedService.update_answer_submitted(
                answer_submitted_id,
                text_answered
            )
            
            if error:
                return None, error

            return updated_answer.to_dict() if updated_answer else None, None

        except Exception as e:
            logger.error(f"Error updating answer submitted in controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_answer_submitted(
        answer_submitted_id: int,
        current_user: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Delete a submitted answer with access control
        
        Args:
            answer_submitted_id: ID of the answer submission
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (Success boolean, Success/Error message)
        """
        try:
            # Get answer for access control
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return False, "Answer submission not found"

            # Access control
            if current_user and user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if answer.form_submission.form.creator.environment_id != user.environment_id:
                        return False, "Unauthorized access"
                elif answer.form_submission.submitted_by != current_user:
                    return False, "Unauthorized access"

                # Check submission age for non-admin users
                submission_age = datetime.utcnow() - answer.form_submission.submitted_at
                if submission_age.days > 7:
                    return False, "Cannot delete answers from submissions older than 7 days"

            success, error = AnswerSubmittedService.delete_answer_submitted(answer_submitted_id)
            if not success:
                return False, error or "Failed to delete answer submission"

            return True, "Answer submission deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting answer submitted in controller: {str(e)}")
            return False, str(e)