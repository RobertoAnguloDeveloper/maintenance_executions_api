from typing import Any, Dict, List, Optional, Tuple
from app.models.form import Form
from app.services.form_service import FormService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

class FormController:
    @staticmethod
    def create_form(title: str, description: str, user_id: int, is_public: bool = False) -> tuple:
        """Create a new form"""
        try:
            return FormService.create_form(
                title=title,
                description=description,
                user_id=user_id,
                is_public=is_public
            )
        except Exception as e:
            logger.error(f"Error in create_form controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_form(form_id: int) -> Optional[Form]:
        """Get a specific form"""
        return FormService.get_form(form_id)
    
    @staticmethod
    def get_forms_by_environment(environment_id: int) -> list:
        """Get forms by environment"""
        try:
            return FormService.get_forms_by_environment(environment_id)
        except Exception as e:
            logger.error(f"Error in get_forms_by_environment controller: {str(e)}")
            return []

    @staticmethod
    def get_forms_by_user(user_id: int) -> list:
        """Get forms created by a user"""
        try:
            return FormService.get_forms_by_user(user_id)
        except Exception as e:
            logger.error(f"Error in get_forms_by_user controller: {str(e)}")
            return []

    @staticmethod
    def get_forms_by_creator(username: str) -> List[Form]:
        """Get forms by creator username"""
        try:
            return FormService.get_forms_by_creator(username)
        except Exception as e:
            logger.error(f"Error in get_forms_by_creator controller: {str(e)}")
            return None

    @staticmethod
    def get_public_forms() -> tuple:
        """Get all public forms"""
        try:
            return FormService.get_public_forms()
        except Exception as e:
            logger.error(f"Error in get_public_forms controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_forms(user) -> list:
        """Get all forms with role-based access"""
        try:
            return FormService.get_all_forms(user)
        except Exception as e:
            logger.error(f"Error in get_all_forms controller: {str(e)}")
            return []

    @staticmethod
    def update_form(form_id: int, **kwargs) -> Dict[str, Any]:
        """Update a form"""
        try:
            form, error = FormService.update_form(form_id, **kwargs)
            
            if error:
                return {"error": error}
                
            if not form:
                return {"error": "Form not found"}
                
            return {
                "message": "Form updated successfully",
                "form": form.to_dict()
            }

        except Exception as e:
            logger.error(f"Error in update_form controller: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def delete_form(form_id: int) -> tuple:
        """Delete a form"""
        try:
            return FormService.delete_form(form_id)
        except Exception as e:
            logger.error(f"Error in delete_form controller: {str(e)}")
            return False, str(e)

    @staticmethod
    def submit_form(form_id: int, username: str, answers: list, attachments: list = None) -> tuple:
        """Submit a form"""
        try:
            return FormService.submit_form(form_id, username, answers, attachments)
        except Exception as e:
            logger.error(f"Error in submit_form controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_form_submissions(form_id: int) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all submissions for a form with proper error handling
        """
        try:
            submissions = FormService.get_form_submissions(form_id)
            return [sub.to_dict() for sub in submissions], None
        except Exception as e:
            logger.error(f"Error getting form submissions: {str(e)}")
            return [], "Error retrieving submissions"

    @staticmethod
    def get_form_statistics(form_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get statistics for a form with proper error handling
        """
        try:
            stats = FormService.get_form_statistics(form_id)
            if stats is None:
                return None, "Error generating statistics"
            return stats, None
        except Exception as e:
            logger.error(f"Error getting form statistics: {str(e)}")
            return None, "Error generating statistics"