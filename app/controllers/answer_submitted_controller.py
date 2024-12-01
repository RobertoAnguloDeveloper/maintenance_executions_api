from app.services.answer_submitted_service import AnswerSubmittedService
from app.utils.permission_manager import RoleType
from typing import Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedController:
    @staticmethod
    def create_answer_submitted(
        form_answers_id: int,
        form_submissions_id: int,
        text_answered: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a new submitted answer
        
        Args:
            form_answers_id: ID of the form answer
            form_submissions_id: ID of the form submission
            text_answered: Optional text answer for text-based questions
            
        Returns:
            tuple: (Created answer submitted data or None, Error message or None)
        """
        try:
            answer_submitted, error = AnswerSubmittedService.create_answer_submitted(
                form_answers_id=form_answers_id,
                form_submissions_id=form_submissions_id,
                text_answered=text_answered
            )
            
            if error:
                return None, error

            return answer_submitted.to_dict(), None

        except Exception as e:
            logger.error(f"Error in create_answer_submitted controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_answers_submitted(user, filters: Dict = None) -> List[Dict]:
        """
        Get all answers submitted based on user role and filters
        
        Args:
            user: Current user object
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
                    filters['environment_id'] = user.environment_id
                else:
                    filters['submitted_by'] = user.username

            answers = AnswerSubmittedService.get_all_answers_submitted(filters)
            return [answer.to_dict() for answer in answers]

        except Exception as e:
            logger.error(f"Error getting answers submitted in controller: {str(e)}")
            return []

    @staticmethod
    def get_answer_submitted(answer_submitted_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get a specific submitted answer
        
        Args:
            answer_submitted_id: ID of the submitted answer
            
        Returns:
            tuple: (Answer submitted data or None, Error message or None)
        """
        try:
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return None, "Answer submission not found"

            return answer.to_dict(), None

        except Exception as e:
            logger.error(f"Error getting answer submitted in controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_answers_by_submission(submission_id: int) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all submitted answers for a form submission
        
        Args:
            submission_id: ID of the form submission
            
        Returns:
            tuple: (List of answer submitted dictionaries, Error message or None)
        """
        try:
            answers = AnswerSubmittedService.get_answers_by_submission(submission_id)
            return [answer.to_dict() for answer in answers], None

        except Exception as e:
            logger.error(f"Error getting answers by submission in controller: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_answer_submitted(
        answer_submitted_id: int,
        text_answered: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Update a submitted answer
        
        Args:
            answer_submitted_id: ID of the answer submission to update
            text_answered: New text answer value
            
        Returns:
            tuple: (Updated answer submitted data or None, Error message or None)
        """
        try:
            answer, error = AnswerSubmittedService.update_answer_submitted(
                answer_submitted_id,
                text_answered
            )
            
            if error:
                return None, error

            return answer.to_dict(), None

        except Exception as e:
            logger.error(f"Error updating answer submitted in controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_answer_submitted(answer_submitted_id: int) -> Tuple[bool, str]:
        """
        Delete a submitted answer
        
        Args:
            answer_submitted_id: ID of the answer submission to delete
            
        Returns:
            tuple: (Success boolean, Success/Error message)
        """
        try:
            success, error = AnswerSubmittedService.delete_answer_submitted(answer_submitted_id)
            if not success:
                return False, error or "Failed to delete answer submission"

            return True, "Answer submission deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting answer submitted in controller: {str(e)}")
            return False, str(e)