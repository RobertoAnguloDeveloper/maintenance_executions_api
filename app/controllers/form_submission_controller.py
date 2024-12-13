from datetime import datetime
from typing import Optional, Tuple
from app.models.form_submission import FormSubmission
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType
import logging

logger = logging.getLogger(__name__)

class FormSubmissionController:
    @staticmethod
    def create_submission(form_id: int, username: str) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """Create a new form submission"""
        return FormSubmissionService.create_submission(form_id, username)

    @staticmethod
    def get_all_submissions(user, filters: dict = None) -> list:
        """
        Get all submissions with role-based filtering
        
        Args:
            user: Current user object
            filters: Optional filters
        """
        if not filters:
            filters = {}
            
        # Apply role-based filtering
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                filters['environment_id'] = user.environment_id
            else:
                filters['submitted_by'] = user.username
                
        return FormSubmissionService.get_all_submissions(filters)

    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        """Get a specific submission"""
        return FormSubmissionService.get_submission(submission_id)

    @staticmethod
    def delete_submission(submission_id: int) -> Tuple[bool, Optional[str]]:
        """Delete a submission"""
        return FormSubmissionService.delete_submission(submission_id)