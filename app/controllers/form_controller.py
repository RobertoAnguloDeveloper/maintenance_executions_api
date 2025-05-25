# app/controllers/form_controller.py

from typing import Any, Dict, List, Optional, Tuple
from app.models.form import Form
from app.services.form_service import FormService
from app.models.user import User # Import User for type hinting
import logging

logger = logging.getLogger(__name__)

class FormController:
    @staticmethod
    def create_form(title: str, description: Optional[str], user_id: int, is_public: bool = False, attachments_required: bool = False) -> tuple: # Added attachments_required
        """Create a new form"""
        try:
            return FormService.create_form(
                title=title,
                description=description,
                user_id=user_id,
                is_public=is_public,
                attachments_required=attachments_required # Pass new field
            )
        except Exception as e:
            logger.error(f"Error in create_form controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_form(form_id: int) -> Optional[Form]:
        """Get a specific form"""
        return FormService.get_form(form_id)

    @staticmethod
    def get_forms_by_environment(environment_id: int, current_user: User) -> list:
        """Get forms by environment"""
        try:
            return FormService.get_forms_by_environment(environment_id, current_user)
        except Exception as e:
            logger.error(f"Error in get_forms_by_environment controller: {str(e)}")
            return []

    @staticmethod
    def get_forms_by_user(user_id: int) -> list: # Deprecate in favor of get_forms_by_creator
        """Get forms created by a user"""
        try:
            # Consider using get_forms_by_creator if username is available or modifying service
            logger.warning("get_forms_by_user is called, consider get_forms_by_creator if username is preferred.")
            return FormService.get_forms_by_user_or_public(user_id=user_id) # Example adaptation
        except Exception as e:
            logger.error(f"Error in get_forms_by_user controller: {str(e)}")
            return []

    @staticmethod
    def get_forms_by_creator(username: str, current_user: User) -> List[Form]:
        """Get forms by creator username"""
        try:
            return FormService.get_forms_by_creator(username, current_user)
        except Exception as e:
            logger.error(f"Error in get_forms_by_creator controller: {str(e)}")
            return [] # Return empty list on error

    @staticmethod
    def get_public_forms(current_user: User) -> List[Form]:
        """Get all public forms"""
        try:
            forms = FormService.get_public_forms(current_user)
            return forms if forms is not None else []
        except Exception as e:
            logger.error(f"Error in get_public_forms controller: {str(e)}")
            return [] # Return empty list on error

    @staticmethod
    def get_all_forms(user) -> list:
        """Get all forms with role-based access"""
        try:
            return FormService.get_all_forms(user)
        except Exception as e:
            logger.error(f"Error in get_all_forms controller: {str(e)}")
            return []

    @staticmethod
    def get_all_forms_basic_info_controller(current_user: User) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Controller method to get basic info for all accessible forms."""
        try:
            return FormService.get_all_forms_basic_info(current_user)
        except Exception as e:
            logger.error(f"Error in get_all_forms_basic_info_controller: {str(e)}")
            return [], "Failed to retrieve basic form information."


    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of forms with pagination
        """
        return FormService.get_batch(page, per_page, **filters)

    @staticmethod
    def update_form(form_id: int, **kwargs) -> Dict[str, Any]:
        """Update a form"""
        try:
            # attachments_required can be in kwargs
            form, error = FormService.update_form(form_id, **kwargs)

            if error:
                return {"error": error}

            if not form: # Should be covered by error but good practice
                return {"error": "Form not found after update attempt"}

            return {
                "message": "Form updated successfully",
                "form": form.to_dict()
            }

        except Exception as e:
            logger.error(f"Error in update_form controller: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def delete_form(form_id: int, current_user: User) -> tuple:
        """Delete a form"""
        try:
            return FormService.delete_form(form_id, current_user)
        except Exception as e:
            logger.error(f"Error in delete_form controller: {str(e)}")
            return False, str(e)

    # submit_form and other methods remain unchanged unless they need to consider form_assignments directly
    # For now, access control to submit a form would be handled by checking if a user can *view* or *interact*
    # with a form based on form_assignments or public status, which should happen in the view layer
    # before calling this controller method.

    @staticmethod
    def submit_form(form_id: int, username: str, answers: list) -> tuple: # Removed attachments from signature
        """Submit a form"""
        try:
            # The service layer's submit_form needs to be updated if it's handling attachments directly
            # This controller method signature has already removed attachments.
            return FormService.submit_form(form_id, username, answers)
        except Exception as e:
            logger.error(f"Error in submit_form controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_form_submissions(form_id: int, current_user: User) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all submissions for a form with proper error handling
        """
        try:
            submissions = FormService.get_form_submissions(form_id, current_user)
            # Ensure submissions are converted to dicts if not already
            return [sub.to_dict() if hasattr(sub, 'to_dict') else sub for sub in submissions], None
        except Exception as e:
            logger.error(f"Error getting form submissions: {str(e)}")
            return [], "Error retrieving submissions"

    @staticmethod
    def get_form_statistics(form_id: int, current_user: User) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get statistics for a form with proper error handling
        """
        try:
            stats = FormService.get_form_statistics(form_id, current_user)
            if stats is None: # Service returns None on error or if form not found
                return None, "Form not found or error generating statistics"
            # Check if service returned an error dict
            if isinstance(stats, dict) and "error" in stats:
                return None, stats["error"]
            return stats, None
        except Exception as e:
            logger.error(f"Error getting form statistics: {str(e)}")
            return None, "Error generating statistics"
