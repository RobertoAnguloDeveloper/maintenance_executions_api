# app/controllers/form_assignment_controller.py

from typing import List, Optional, Tuple, Dict, Any
from app.controllers.user_controller import UserController
from app.services.form_assignment_service import FormAssignmentService
from app.models.user import User
from app.services.form_service import FormService
import logging

logger = logging.getLogger(__name__)

class FormAssignmentController:

    @staticmethod
    def create_form_assignment(form_id: int, entity_name: str, entity_id: int, current_user: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new form assignment. current_user is for authorization checks."""
        form = FormService.get_form(form_id)
        if not form:
            return None, f"Form with ID {form_id} not found."

        is_super_user = current_user.role and current_user.role.is_super_user
        if form.user_id != current_user.id and not is_super_user:
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
        Non-admins can only assign forms they own.
        """
        if not isinstance(assignments_data, list):
            return None, "Invalid input: Expected a list of assignment objects."
        if not all(isinstance(item, dict) for item in assignments_data):
            return None, "Invalid input: Each item in the list must be an assignment object (dictionary)."

        for item in assignments_data:
            if not all(key in item and isinstance(item.get('form_id'), int) and
                       isinstance(item.get('entity_name'), str) and item.get('entity_name', '').strip() and
                       isinstance(item.get('entity_id'), int)
                       for key in ['form_id', 'entity_name', 'entity_id']):
                 return None, f"Invalid input: Each assignment object must contain 'form_id' (int), 'entity_name' (non-empty str), and 'entity_id' (int). Problematic item: {item}"

        results = FormAssignmentService.create_bulk_form_assignments(assignments_data, current_user=current_user)
        return results, None

    @staticmethod
    def get_assignments_for_form(form_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get all assignments for a specific form. current_user for auth."""
        form = FormService.get_form(form_id)
        if not form:
            return None, f"Form with ID {form_id} not found."

        is_super_user = current_user.role and current_user.role.is_super_user
        if form.user_id != current_user.id and not is_super_user:
            logger.warning(f"User {current_user.id} unauthorized to view assignments for form {form_id}.")
            return None, "Unauthorized to view assignments for this form."

        assignments = FormAssignmentService.get_assignments_for_form(form_id)
        return [a.to_dict() for a in assignments], None

    @staticmethod
    def get_forms_for_entity(entity_name: str, entity_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Get all forms assigned to a specific entity.
        Restricted for non-admins to view only for themselves if entity_name is 'user',
        or denied for 'role'/'environment'.
        """
        is_super_user = current_user.role and current_user.role.is_super_user

        if entity_name not in FormAssignmentService.VALID_ENTITY_NAMES:
             return None, f"Invalid entity_name: {entity_name}. Must be one of {FormAssignmentService.VALID_ENTITY_NAMES}."

        if not is_super_user:
            if entity_name == 'user':
                if entity_id != current_user.id:
                    return None, "Unauthorized: Can only view assignments for your own user."
            elif entity_name in ['role', 'environment']:
                 return None, f"Unauthorized: Only administrators can view forms for {entity_name} entities."

        forms = FormAssignmentService.get_forms_for_entity(entity_name, entity_id)
        return [f.to_dict_basic() if hasattr(f, 'to_dict_basic') else f.to_dict() for f in forms], None

    @staticmethod
    def get_accessible_forms_for_user(user_id: int, current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Get all forms a specific user has access to.
        Restricted to admin or self-view.
        """
        is_super_user = current_user.role and current_user.role.is_super_user
        if user_id != current_user.id and not is_super_user:
            return None, "Unauthorized to view accessible forms for this user."

        forms = FormAssignmentService.get_accessible_forms_for_user(user_id)
        return [f.to_dict_basic() if hasattr(f, 'to_dict_basic') else f.to_dict() for f in forms], None

    @staticmethod
    def delete_form_assignment(assignment_id: int, current_user: User) -> Tuple[bool, Optional[str]]:
        """Delete a form assignment. current_user for auth."""
        assignment = FormAssignmentService.get_form_assignment_by_id(assignment_id)
        if not assignment:
            return False, "Form assignment not found or already deleted."

        form = FormService.get_form(assignment.form_id)
        if not form:
            logger.error(f"Consistency issue: Assignment {assignment_id} exists for non-existent/deleted form {assignment.form_id}")
            return False, "Associated form not found. Cannot determine authorization."

        is_super_user = current_user.role and current_user.role.is_super_user
        if form.user_id != current_user.id and not is_super_user:
            logger.warning(f"User {current_user.id} unauthorized to delete assignment {assignment_id} for form {form.id}.")
            return False, "Unauthorized to delete this form assignment. You must be the form owner or an administrator."

        return FormAssignmentService.delete_form_assignment(assignment_id)

    @staticmethod
    def check_user_access_to_form(user_id: int, form_id: int, current_user: User) -> Tuple[Optional[Dict[str, bool]], Optional[str]]:
        """Check if a user has access to a form. current_user for auth."""
        is_super_user = current_user.role and current_user.role.is_super_user
        if user_id != current_user.id and not is_super_user:
             return None, "Unauthorized to check access for this user."

        has_access = FormAssignmentService.check_user_access_to_form(user_id, form_id, user_obj=current_user if user_id == current_user.id else None)
        return {"user_id": user_id, "form_id": form_id, "has_access": has_access}, None

    @staticmethod
    def get_assignments_batch(page: int, per_page: int, current_user: User) -> Tuple[Optional[Tuple[int, List[Dict]]], Optional[str]]:
        """Get form assignments in a paginated batch. Filters by ownership for non-admins."""
        total_count, assignments = FormAssignmentService.get_assignments_batch_paginated(page, per_page, current_user=current_user)
        assignments_dict = [a.to_dict() for a in assignments]
        return (total_count, assignments_dict), None

    @staticmethod
    def get_all_assignments_unpaginated_controller(current_user: User) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """Get ALL form assignments (unpaginated). Filters by ownership for non-admins."""
        assignments = FormAssignmentService.get_all_assignments_unpaginated(current_user=current_user)
        assignments_dict = [a.to_dict() for a in assignments]
        return assignments_dict, None

    @staticmethod
    def update_form_assignment(assignment_id: int, update_data: Dict[str, Any], current_user: User) -> Tuple[Optional[Dict], Optional[str]]:
        """Update an existing form assignment. current_user for authorization checks."""
        assignment = FormAssignmentService.get_form_assignment_by_id(assignment_id)
        if not assignment:
            return None, "Form assignment not found or already deleted."

        form = FormService.get_form(assignment.form_id)
        if not form:
            logger.error(f"Consistency issue: Assignment {assignment_id} exists for non-existent/deleted form {assignment.form_id}")
            return None, "Associated form not found. Cannot determine authorization."

        is_super_user = current_user.role and current_user.role.is_super_user
        if form.user_id != current_user.id and not is_super_user:
            logger.warning(f"User {current_user.id} unauthorized to update assignment {assignment_id} for form {form.id}.")
            return None, "Unauthorized to update this form assignment. You must be the form owner or an administrator."

        updated_assignment, error = FormAssignmentService.update_form_assignment(assignment_id, update_data)

        if error:
            return None, error

        return updated_assignment.to_dict() if updated_assignment else None, None