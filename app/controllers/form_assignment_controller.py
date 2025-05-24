# app/controllers/form_assignment_controller.py

from typing import List, Optional, Tuple, Dict
from app.services.form_assignment_service import FormAssignmentService
from app.models.user import User # For type hinting if needed for auth checks
import logging

logger = logging.getLogger(__name__)

class FormAssignmentController:
    @staticmethod
    def create_form_assignment(form_id: int, entity_name: str, entity_id: int, current_user: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new form assignment. current_user is for authorization checks."""
        # Add authorization checks here if needed, e.g., only form owner or admin can assign
        # For example:
        # from app.services.form_service import FormService
        # form = FormService.get_form(form_id)
        # if not form or (form.user_id != current_user.id and not current_user.role.is_super_user):
        #     return None, "Unauthorized to assign this form."
            
        assignment, error = FormAssignmentService.create_form_assignment(form_id, entity_name, entity_id)
        if error:
            return None, error
        return assignment.to_dict() if assignment else None, None

    @staticmethod
    def get_assignments_for_form(form_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all assignments for a specific form. current_user for auth."""
        # Add authorization: e.g., only form owner/admin can see all assignments for a form
        assignments = FormAssignmentService.get_assignments_for_form(form_id)
        return [a.to_dict() for a in assignments], None

    @staticmethod
    def get_forms_for_entity(entity_name: str, entity_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all forms assigned to a specific entity. current_user for auth."""
        # Add authorization: e.g., if entity_name is 'user', check if current_user is that user or admin
        forms = FormAssignmentService.get_forms_for_entity(entity_name, entity_id)
        return [f.to_dict_basic() for f in forms], None # Using to_dict_basic for lists of forms
        
    @staticmethod
    def get_accessible_forms_for_user(user_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all forms a specific user has access to. current_user for auth."""
        # Add authorization: e.g., user can only request their own accessible forms, or admin can request for any user
        if user_id != current_user.id and not current_user.role.is_super_user:
            return None, "Unauthorized to view accessible forms for this user."
            
        forms = FormAssignmentService.get_accessible_forms_for_user(user_id)
        return [f.to_dict_basic() for f in forms], None

    @staticmethod
    def delete_form_assignment(assignment_id: int, current_user: User) -> Tuple[bool, Optional[str]]:
        """Delete a form assignment. current_user for auth."""
        # Add authorization checks here: e.g., only form owner or admin can delete assignments
        return FormAssignmentService.delete_form_assignment(assignment_id)
        
    @staticmethod
    def check_user_access_to_form(user_id: int, form_id: int, current_user: User) -> Tuple[Optional[Dict[str, bool]], Optional[str]]:
        """Check if a user has access to a form. current_user for auth."""
        if user_id != current_user.id and not current_user.role.is_super_user:
             return None, "Unauthorized to check access for this user."
        has_access = FormAssignmentService.check_user_access_to_form(user_id, form_id)
        return {"user_id": user_id, "form_id": form_id, "has_access": has_access}, None