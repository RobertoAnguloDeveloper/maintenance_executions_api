# app/services/form_assignment_service.py

from typing import List, Optional, Tuple, Union, Dict
from app import db
from app.models.form import Form
from app.models.form_assignment import FormAssignment
from app.models.user import User
from app.models.role import Role
from app.models.environment import Environment
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload # For eager loading form creator
import logging

logger = logging.getLogger(__name__)

class FormAssignmentService:
    VALID_ENTITY_NAMES = ['user', 'role', 'environment'] # Define valid assignable entities

    @staticmethod
    def _validate_entity(entity_name: str, entity_id: int) -> Tuple[bool, Optional[str]]:
        """Validate if the entity exists and is active."""
        if entity_name not in FormAssignmentService.VALID_ENTITY_NAMES:
            return False, f"Invalid entity_name: {entity_name}. Must be one of {FormAssignmentService.VALID_ENTITY_NAMES}."

        model_map = {
            'user': User,
            'role': Role,
            'environment': Environment
        }
        model_class = model_map.get(entity_name)
        if not model_class:
            return False, f"Internal error: No model class mapped for entity_name {entity_name}."

        entity = model_class.query.filter_by(id=entity_id, is_deleted=False).first()
        if not entity:
            return False, f"{entity_name.capitalize()} with ID {entity_id} not found or is deleted."
        return True, None

    @staticmethod
    def create_form_assignment(form_id: int, entity_name: str, entity_id: int) -> Tuple[Optional[FormAssignment], Optional[str]]:
        """Create a new form assignment."""
        try:
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, f"Form with ID {form_id} not found or is deleted."

            is_valid_entity, entity_error = FormAssignmentService._validate_entity(entity_name, entity_id)
            if not is_valid_entity:
                return None, entity_error

            existing_assignment = FormAssignment.query.filter_by(
                form_id=form_id,
                entity_name=entity_name,
                entity_id=entity_id,
                is_deleted=False
            ).first()
            if existing_assignment:
                return None, f"This form is already actively assigned to {entity_name} ID {entity_id}."

            new_assignment = FormAssignment(
                form_id=form_id,
                entity_name=entity_name,
                entity_id=entity_id
            )
            db.session.add(new_assignment)
            db.session.commit()
            logger.info(f"Form {form_id} assigned to {entity_name} ID {entity_id}.")
            return new_assignment, None
        except IntegrityError:
            db.session.rollback()
            logger.error(f"Integrity error creating form assignment for form {form_id} to {entity_name} ID {entity_id}.")
            return None, "Database integrity error. This assignment might already exist (check unique constraints) or form/entity ID is invalid."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form assignment: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_form_assignment_by_id(assignment_id: int) -> Optional[FormAssignment]:
        """Get a form assignment by its ID."""
        return FormAssignment.query.filter_by(id=assignment_id, is_deleted=False).first()

    @staticmethod
    def get_assignments_for_form(form_id: int) -> List[FormAssignment]:
        """Get all active assignments for a specific form."""
        return FormAssignment.query.filter_by(form_id=form_id, is_deleted=False).all()

    @staticmethod
    def get_forms_for_entity(entity_name: str, entity_id: int) -> List[Form]:
        """Get all active forms assigned to a specific entity."""
        is_valid_entity, entity_error = FormAssignmentService._validate_entity(entity_name, entity_id)
        if not is_valid_entity:
            logger.warning(f"Attempt to get forms for invalid entity: {entity_name} ID {entity_id}. Error: {entity_error}")
            return []

        assignments = FormAssignment.query.filter_by(
            entity_name=entity_name,
            entity_id=entity_id,
            is_deleted=False
        ).join(Form).filter(Form.is_deleted == False).all() # Ensure the linked form is also not deleted
        return [assignment.form for assignment in assignments]

    @staticmethod
    def check_user_access_to_form(user_id: int, form_id: int) -> bool:
        """
        Check if a user has access to a specific form based on new assignment rules.
        """
        user = User.query.options(joinedload(User.role)).filter_by(id=user_id, is_deleted=False).first() # Eager load role
        if not user:
            logger.warning(f"Access check failed: User ID {user_id} not found or deleted.")
            return False

        form = Form.query.options(joinedload(Form.creator)).filter_by(id=form_id, is_deleted=False).first() # Eager load creator
        if not form:
            logger.warning(f"Access check failed: Form ID {form_id} not found or deleted.")
            return False
        
        # 1. Admin Override
        if user.role and user.role.is_super_user: #
            logger.debug(f"Access granted for form {form_id} to admin user {user_id}.")
            return True

        # 2. Creator Override
        if form.user_id == user_id: #
            logger.debug(f"Access granted for form {form_id} to creator user {user_id}.")
            return True

        # 3. Fetch active assignments for the form
        active_assignments = FormAssignment.query.filter_by(form_id=form_id, is_deleted=False).all()

        if active_assignments:
            # If assignments exist, access is exclusively determined by them.
            logger.debug(f"Form {form_id} has active assignments. Checking against user {user_id}.")
            for assignment in active_assignments:
                if assignment.entity_name == 'user' and assignment.entity_id == user_id:
                    logger.debug(f"Access granted for form {form_id} to user {user_id} via direct user assignment.")
                    return True
                if user.role_id and assignment.entity_name == 'role' and assignment.entity_id == user.role_id:
                    logger.debug(f"Access granted for form {form_id} to user {user_id} via role assignment (role ID: {user.role_id}).")
                    return True
                if user.environment_id and assignment.entity_name == 'environment' and assignment.entity_id == user.environment_id:
                    logger.debug(f"Access granted for form {form_id} to user {user_id} via environment assignment (env ID: {user.environment_id}).")
                    return True
            logger.debug(f"Access denied for form {form_id} to user {user_id}. No matching assignments.")
            return False # No matching assignment found
        else:
            # No active assignments: default behavior applies
            logger.debug(f"Form {form_id} has no active assignments. Applying default access rules for user {user_id}.")
            # 4. Public Form (if no assignments)
            if form.is_public: #
                logger.debug(f"Access granted for form {form_id} to user {user_id} because it's public and has no assignments.")
                return True
            
            # 5. Same Environment as Creator (if no assignments and not public)
            if form.creator and form.creator.environment_id == user.environment_id: #
                logger.debug(f"Access granted for form {form_id} to user {user_id} (env ID: {user.environment_id}) as it's in the creator's environment (env ID: {form.creator.environment_id}) and has no assignments.")
                return True
            
            logger.debug(f"Access denied for form {form_id} to user {user_id}. Not public, not in creator's environment, and no assignments.")
            return False

    @staticmethod
    def get_accessible_forms_for_user(user_id: int) -> List[Form]:
        """
        Get all forms a user has access to, respecting the new assignment-based logic.
        This implementation iterates through all non-deleted forms and applies
        the check_user_access_to_form logic. This is correct but may be less performant
        for very large numbers of forms. For significantly large datasets,
        more complex SQL queries might be needed.
        """
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        if not user:
            logger.warning(f"Cannot get accessible forms: User ID {user_id} not found or deleted.")
            return []

        # If admin, fetch all non-deleted forms
        if user.role and user.role.is_super_user: #
            logger.debug(f"Admin user {user_id} retrieving all non-deleted forms.")
            return Form.query.filter_by(is_deleted=False).order_by(Form.title).all()

        accessible_forms = []
        all_forms = Form.query.filter_by(is_deleted=False).options(
            joinedload(Form.creator).joinedload(User.environment), # Eager load for env check
            joinedload(Form.form_assignments) # Eager load assignments for checks
        ).all()

        for form_item in all_forms:
            # We pass the already fetched user object to check_user_access_to_form
            # to avoid re-fetching it repeatedly.
            # However, check_user_access_to_form as written re-fetches user and form.
            # For optimization, check_user_access_to_form could accept pre-fetched objects.
            # For now, we rely on its current signature for clarity.
            if FormAssignmentService.check_user_access_to_form(user_id, form_item.id):
                accessible_forms.append(form_item)
        
        logger.info(f"User {user_id} has access to {len(accessible_forms)} forms.")
        return sorted(accessible_forms, key=lambda f: f.title) # Sort for consistent output


    @staticmethod
    def delete_form_assignment(assignment_id: int) -> Tuple[bool, Optional[str]]:
        """Soft delete a form assignment."""
        try:
            assignment = FormAssignment.query.filter_by(id=assignment_id, is_deleted=False).first() #
            if not assignment:
                return False, "Form assignment not found or already deleted."

            assignment.soft_delete() #
            db.session.commit()
            logger.info(f"Form assignment ID {assignment_id} soft-deleted.")
            return True, None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting form assignment ID {assignment_id}: {str(e)}")
            return False, str(e)