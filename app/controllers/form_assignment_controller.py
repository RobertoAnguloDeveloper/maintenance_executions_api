# app/controllers/form_assignment_controller.py

from typing import List, Optional, Tuple, Dict, Any
from app.services.form_assignment_service import FormAssignmentService
from app.models.user import User # For type hinting if needed for auth checks
from app.services.form_service import FormService # For authorization checks
import logging

logger = logging.getLogger(__name__)

class FormAssignmentController:
    @staticmethod
    def create_form_assignment(form_id: int, entity_name: str, entity_id: int, current_user: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new form assignment. current_user is for authorization checks."""
        # Authorization: Check if current_user owns the form or is an admin
        form = FormService.get_form_by_id(form_id) # Assuming FormService has this method
        if not form:
            return None, f"Form with ID {form_id} not found."
        if form.user_id != current_user.id and not (current_user.role and current_user.role.is_super_user):
            logger.warning(f"User {current_user.id} unauthorized to assign form {form_id}.")
            return None, "Unauthorized to assign this form. You must be the form owner or an administrator."
            
        assignment, error = FormAssignmentService.create_form_assignment(form_id, entity_name, entity_id)
        if error:
            return None, error
        return assignment.to_dict() if assignment else None, None

    @staticmethod
    def create_bulk_form_assignments(assignments_data: List[Dict[str, Any]], current_user: User) -> Tuple[Optional[Dict[str, List[Any]]], Optional[str]]:
        """
        Create multiple form assignments in bulk.
        assignments_data: List of dicts, each with 'form_id', 'entity_name', 'entity_id'.
        current_user: For authorization checks.
        """
        # Authorization: For bulk operations, typically stricter.
        # Option 1: Only super_user can perform bulk assignments.
        if not (current_user.role and current_user.role.is_super_user):
            logger.warning(f"User {current_user.id} (role: {current_user.role_id}) attempted bulk assignment without super_user privileges.")
            return None, "Unauthorized: Bulk assignment is restricted to administrators."

        # Option 2 (more granular, but complex for bulk):
        # Check ownership for each form_id in assignments_data.
        # This would require iterating through assignments_data here or passing current_user to the service
        # for individual checks. For simplicity, sticking with admin-only for bulk.
        # If granular checks are needed, the service method would need to be adapted or pre-checks done here.

        # Validate input structure
        if not isinstance(assignments_data, list):
            return None, "Invalid input: Expected a list of assignment objects."
        if not all(isinstance(item, dict) for item in assignments_data):
            return None, "Invalid input: Each item in the list must be an assignment object (dictionary)."
        
        for item in assignments_data:
            if not all(key in item for key in ['form_id', 'entity_name', 'entity_id']):
                 return None, f"Invalid input: Each assignment object must contain 'form_id', 'entity_name', and 'entity_id'. Problematic item: {item}"


        results = FormAssignmentService.create_bulk_form_assignments(assignments_data)
        return results, None


    @staticmethod
    def get_assignments_for_form(form_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all assignments for a specific form. current_user for auth."""
        form = FormService.get_form_by_id(form_id)
        if not form:
            return None, f"Form with ID {form_id} not found."
        if form.user_id != current_user.id and not (current_user.role and current_user.role.is_super_user):
            logger.warning(f"User {current_user.id} unauthorized to view assignments for form {form_id}.")
            return None, "Unauthorized to view assignments for this form."

        assignments = FormAssignmentService.get_assignments_for_form(form_id)
        return [a.to_dict() for a in assignments], None

    @staticmethod
    def get_forms_for_entity(entity_name: str, entity_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all forms assigned to a specific entity. current_user for auth."""
        # Authorization: If entity is 'user', only that user or admin. Other entities might be admin-only.
        if entity_name == 'user' and entity_id != current_user.id and not (current_user.role and current_user.role.is_super_user):
            return None, "Unauthorized to view forms for this user."
        # Add more specific checks for 'role' or 'environment' if needed, e.g., admin only
        elif entity_name in ['role', 'environment'] and not (current_user.role and current_user.role.is_super_user):
             return None, f"Unauthorized to view forms for {entity_name} entities."


        forms = FormAssignmentService.get_forms_for_entity(entity_name, entity_id)
        # Assuming forms returned by the service are Form model instances
        return [f.to_dict_basic() if hasattr(f, 'to_dict_basic') else f.to_dict() for f in forms], None
        
    @staticmethod
    def get_accessible_forms_for_user(user_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all forms a specific user has access to. current_user for auth."""
        if user_id != current_user.id and not (current_user.role and current_user.role.is_super_user):
            return None, "Unauthorized to view accessible forms for this user."
            
        forms = FormAssignmentService.get_accessible_forms_for_user(user_id)
        return [f.to_dict_basic() if hasattr(f, 'to_dict_basic') else f.to_dict() for f in forms], None

    @staticmethod
    def delete_form_assignment(assignment_id: int, current_user: User) -> Tuple[bool, Optional[str]]:
        """Delete a form assignment. current_user for auth."""
        assignment = FormAssignmentService.get_form_assignment_by_id(assignment_id)
        if not assignment:
            return False, "Form assignment not found or already deleted."

        form = FormService.get_form_by_id(assignment.form_id)
        if not form: # Should ideally not happen if assignment exists and FKs are in place
            logger.error(f"Consistency issue: Assignment {assignment_id} exists for non-existent/deleted form {assignment.form_id}")
            return False, "Associated form not found. Cannot determine authorization."

        if form.user_id != current_user.id and not (current_user.role and current_user.role.is_super_user):
            logger.warning(f"User {current_user.id} unauthorized to delete assignment {assignment_id} for form {form.id}.")
            return False, "Unauthorized to delete this form assignment. You must be the form owner or an administrator."
            
        return FormAssignmentService.delete_form_assignment(assignment_id)
        
    @staticmethod
    def check_user_access_to_form(user_id: int, form_id: int, current_user: User) -> Tuple[Optional[Dict[str, bool]], Optional[str]]:
        """Check if a user has access to a form. current_user for auth."""
        # Authorization for *checking* access:
        # User can check their own access. Admin can check for any user.
        if user_id != current_user.id and not (current_user.role and current_user.role.is_super_user):
             return None, "Unauthorized to check access for this user."
        
        has_access = FormAssignmentService.check_user_access_to_form(user_id, form_id)
        return {"user_id": user_id, "form_id": form_id, "has_access": has_access}, None
