from typing import Dict, List, Optional, Tuple
from flask import current_app
from app.models import user
from app.models.answer_submitted import AnswerSubmitted
from app.services.answer_submitted_service import AnswerSubmittedService
from app.services.form_submission_service import FormSubmissionService
from app.services.form_service import FormService
from app.utils.permission_manager import RoleType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedController:
    @staticmethod
    def create_answer_submitted(
        form_submission_id: int,
        question_text: str,
        question_type_text: str,
        answer_text: str,
        current_user: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"

            # Only submission owner can add answers
            if current_user and submission.submitted_by != current_user:
                return None, "Unauthorized: Can only add answers to own submissions"

            answer_submitted, error = AnswerSubmittedService.create_answer_submitted(
                form_submission_id=form_submission_id,
                question_text=question_text,
                question_type_text=question_type_text,
                answer_text=answer_text
            )
            
            if error:
                return None, error

            return answer_submitted.to_dict() if answer_submitted else None, None

        except Exception as e:
            logger.error(f"Error in create_answer_submitted controller: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def bulk_create_answers_submitted(
        form_submission_id: int,
        submissions_data: List[Dict],
        current_user: str = None
    ) -> Tuple[Optional[List[AnswerSubmitted]], Optional[str]]:
        """
        Bulk create answer submissions with validation
        
        Args:
            form_submission_id: ID of the form submission
            submissions_data: List of submission data dictionaries
            current_user: Username of current user
            
        Returns:
            tuple: (List of created AnswerSubmitted objects or None, Error message or None)
        """
        try:
            # Validate submission exists and check access rights
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"
                    
            # Only submission owner can add answers
            if current_user and submission.submitted_by != current_user:
                return None, "Unauthorized: Can only add answers to own submissions"

            created_submissions, error = AnswerSubmittedService.bulk_create_answers_submitted(
                form_submission_id=form_submission_id,
                answers_data=submissions_data
            )
            
            if error:
                return None, error
                    
            return created_submissions, None

        except Exception as e:
            logger.error(f"Error in bulk_create_answers_submitted controller: {str(e)}")
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
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of submitted answers with pagination
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, answers_submitted)
        """
        return AnswerSubmittedService.get_batch(page, per_page, **filters)

        
    @staticmethod
    def get_answer_submitted(
        answer_submitted_id: int,
        current_user: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get a specific submitted answer with authorization checks.
        
        Args:
            answer_submitted_id: ID of the answer submission
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (Answer submitted dictionary or None, Error message or None)
        """
        try:
            # Get the answer submission
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return None, "Answer submission not found"

            # Access control
            if current_user and user_role != RoleType.ADMIN:
                # Get the current user object to check environment_id
                user_obj = user.User.query.filter_by(username=current_user).first()
                
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if answer.form_submission.form.creator.environment_id != user_obj.environment_id:
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
        """Get all submitted answers for a form submission"""
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
        answer_text: Optional[str] = None,
        current_user: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Update a submitted answer"""
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

            # Check submission age for non-admin users
            if user_role != RoleType.ADMIN:
                submission_age = datetime.utcnow() - answer.form_submission.submitted_at
                if submission_age.days > 7:  # Configurable timeframe
                    return None, "Cannot update answers older than 7 days"

            updated_answer, error = AnswerSubmittedService.update_answer_submitted(
                answer_submitted_id,
                answer_text
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
        """Delete a submitted answer"""
        try:
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
            if user_role != RoleType.ADMIN:
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