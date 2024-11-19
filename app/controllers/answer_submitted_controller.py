# app/controllers/answer_submitted_controller.py

from app.services.answer_submitted_service import AnswerSubmittedService
from app.utils.permission_manager import RoleType
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedController:
    @staticmethod
    def create_answer_submitted(form_answers_id, form_submissions_id):
        """Create a new submitted answer"""
        return AnswerSubmittedService.create_answer_submitted(
            form_answers_id=form_answers_id,
            form_submissions_id=form_submissions_id
        )
        
    @staticmethod
    def get_all_answers_submitted(user, filters: dict = None) -> list:
        """
        Get all answers submitted based on user role and filters
        
        Args:
            user: Current user object
            filters (dict): Optional filters
            
        Returns:
            list: List of AnswerSubmitted objects
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
                        
            return AnswerSubmittedService.get_all_answers_submitted(filters)
                
        except Exception as e:
            logger.error(f"Error getting answers submitted in controller: {str(e)}")
            return []

    @staticmethod
    def get_answer_submitted(answer_submitted_id):
        """Get a specific submitted answer"""
        return AnswerSubmittedService.get_answer_submitted(answer_submitted_id)

    @staticmethod
    def get_answers_by_submission(submission_id):
        """Get all submitted answers for a form submission"""
        return AnswerSubmittedService.get_answers_by_submission(submission_id)

    @staticmethod
    def delete_answer_submitted(answer_submitted_id):
        """Delete a submitted answer"""
        return AnswerSubmittedService.delete_answer_submitted(answer_submitted_id)