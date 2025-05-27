# app/services/form_assignment_service.py

from typing import List, Optional, Tuple, Union, Dict, Any
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
            logger.error(f"Internal error: No model class mapped for entity_name {entity_name}.")
            return False, f"Internal error: No model class mapped for entity_name {entity_name}."

        entity = model_class.query.filter_by(id=entity_id).first()
        if not entity:
            return False, f"{entity_name.capitalize()} with ID {entity_id} not found."
        if hasattr(entity, 'is_deleted') and entity.is_deleted:
            return False, f"{entity_name.capitalize()} with ID {entity_id} is deleted."

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
            logger.info(f"Form {form_id} assigned to {entity_name} ID {entity_id}. Assignment ID: {new_assignment.id}")
            return new_assignment, None
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating form assignment for form {form_id} to {entity_name} ID {entity_id}: {e}", exc_info=True)
            if hasattr(e, 'orig') and e.orig and ("UniqueViolation" in str(type(e.orig).__name__) or "_form_entity_uc" in str(e.orig)):
                 return None, f"Database integrity error: This form is already assigned to {entity_name} ID {entity_id} (possibly soft-deleted but unique constraint still applies to non-deleted entries)."
            return None, "Database integrity error. Please check form/entity ID validity or potential unique constraint issues."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form assignment for form {form_id}, {entity_name} {entity_id}: {str(e)}", exc_info=True)
            return None, f"An unexpected error occurred: {str(e)}"

    @staticmethod
    def create_bulk_form_assignments(assignments_data: List[Dict[str, Any]], current_user: User) -> Dict[str, List[Any]]:
        """
        Create multiple form assignments in bulk.
        Each item in assignments_data should be a dict with 'form_id', 'entity_name', 'entity_id'.
        If current_user is not an admin, only allows assignments for forms they own.
        """
        successful_assignment_models = []
        processed_successful_for_return = []
        failed_assignments_for_return = []

        is_admin = current_user.role and current_user.role.is_super_user

        # --- MODIFICATION START: Fetch relevant forms based on ownership if not admin ---
        form_ids_in_request = list(set(
            item.get('form_id') for item in assignments_data
            if isinstance(item, dict) and isinstance(item.get('form_id'), int)
        ))

        # Query forms: if admin, get all requested forms; if not admin, only get owned forms.
        forms_query = Form.query.filter(Form.id.in_(form_ids_in_request), Form.is_deleted == False)
        if not is_admin:
            forms_query = forms_query.filter(Form.user_id == current_user.id)
        
        accessible_forms_map = {form.id: form for form in forms_query.all()}
        # --- MODIFICATION END ---

        for item_data in assignments_data:
            if not isinstance(item_data, dict):
                failed_assignments_for_return.append({"input": item_data, "error": "Invalid item format: Expected a dictionary."})
                continue

            form_id = item_data.get('form_id')
            entity_name = item_data.get('entity_name')
            entity_id = item_data.get('entity_id')
            original_input = {"form_id": form_id, "entity_name": entity_name, "entity_id": entity_id}

            if not (isinstance(form_id, int) and
                    isinstance(entity_name, str) and entity_name.strip() and
                    isinstance(entity_id, int)):
                failed_assignments_for_return.append({"input": original_input, "error": "Invalid data types for form_id, entity_name, or entity_id."})
                continue

            # --- MODIFICATION START: Use pre-fetched accessible_forms_map for ownership check ---
            if form_id not in accessible_forms_map:
                failed_assignments_for_return.append({
                    "input": original_input,
                    "error": f"Form with ID {form_id} not found, is deleted, or you do not have permission to assign it."
                })
                continue
            # --- MODIFICATION END ---

            is_valid_entity, entity_error = FormAssignmentService._validate_entity(entity_name, entity_id)
            if not is_valid_entity:
                failed_assignments_for_return.append({"input": original_input, "error": entity_error})
                continue

            try:
                existing_assignment = FormAssignment.query.filter_by(
                    form_id=form_id, entity_name=entity_name, entity_id=entity_id, is_deleted=False
                ).first()
                if existing_assignment:
                    failed_assignments_for_return.append({"input": original_input, "error": f"This form is already actively assigned to {entity_name} ID {entity_id}."})
                    continue

                new_assignment = FormAssignment(form_id=form_id, entity_name=entity_name, entity_id=entity_id)
                db.session.add(new_assignment)
                successful_assignment_models.append({"model": new_assignment, "input_data": original_input})

            except Exception as e:
                logger.error(f"Unexpected error during bulk processing for {original_input}: {str(e)}", exc_info=True)
                failed_assignments_for_return.append({"input": original_input, "error": f"An unexpected error occurred while processing this item: {str(e)}"})

        if successful_assignment_models:
            try:
                db.session.commit()
                for item in successful_assignment_models:
                    processed_successful_for_return.append({
                        "form_id": item["input_data"]["form_id"],
                        "entity_name": item["input_data"]["entity_name"],
                        "entity_id": item["input_data"]["entity_id"],
                        "assignment_id": item["model"].id
                    })
                    logger.info(f"Bulk: Form {item['input_data']['form_id']} assigned to {item['input_data']['entity_name']} ID {item['input_data']['entity_id']}. Assignment ID: {item['model'].id}")
            except IntegrityError as e:
                db.session.rollback()
                logger.error(f"Integrity error during bulk commit: {e}", exc_info=True)
                for item in successful_assignment_models:
                     failed_assignments_for_return.append({"input": item["input_data"], "error": "Database integrity error during bulk commit."})
                processed_successful_for_return = []
            except Exception as e:
                db.session.rollback()
                logger.error(f"Generic error during bulk commit: {e}", exc_info=True)
                for item in successful_assignment_models:
                     failed_assignments_for_return.append({"input": item["input_data"], "error": f"An unexpected error occurred during bulk commit: {str(e)}"})
                processed_successful_for_return = []

        return {
            "successful_assignments": processed_successful_for_return,
            "failed_assignments": failed_assignments_for_return
        }

    @staticmethod
    def get_form_assignment_by_id(assignment_id: int) -> Optional[FormAssignment]:
        """Get a form assignment by its ID."""
        return FormAssignment.query.options(
            joinedload(FormAssignment.form).joinedload(Form.creator)
        ).filter_by(id=assignment_id, is_deleted=False).first()


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
        ).join(Form).filter(Form.is_deleted == False).all()
        return [assignment.form for assignment in assignments]

    @staticmethod
    def check_user_access_to_form(user_id: int, form_id: int, user_obj: Optional[User] = None, form_obj: Optional[Form] = None) -> bool:
        """
        Check if a user has access to a specific form based on new assignment rules.
        Can accept pre-fetched user_obj and form_obj for optimization.
        """
        if user_obj is None or (hasattr(user_obj, 'is_deleted') and user_obj.is_deleted):
            user = User.query.options(joinedload(User.role), joinedload(User.environment)).filter_by(id=user_id, is_deleted=False).first()
        else:
            user = user_obj

        if not user:
            logger.warning(f"Access check failed: User ID {user_id} not found or deleted.")
            return False

        if form_obj is None or (hasattr(form_obj, 'is_deleted') and form_obj.is_deleted):
            form = Form.query.options(
                joinedload(Form.creator).options(joinedload(User.environment)),
                joinedload(Form.form_assignments)
            ).filter_by(id=form_id, is_deleted=False).first()
        else:
            form = form_obj

        if not form:
            logger.warning(f"Access check failed: Form ID {form_id} not found or deleted.")
            return False

        if user.role and user.role.is_super_user:
            logger.debug(f"Access granted for form {form.id} to admin user {user.id}.")
            return True

        if form.user_id == user.id: # Creator access
            logger.debug(f"Access granted for form {form.id} to creator user {user.id}.")
            return True

        active_assignments = []
        if form_obj and hasattr(form_obj, 'form_assignments') and form_obj.form_assignments is not None:
            # Ensure we only consider non-deleted assignments if form_obj is pre-loaded
            active_assignments = [assign for assign in form_obj.form_assignments if hasattr(assign, 'is_deleted') and not assign.is_deleted]
        else: # Fetch assignments if not pre-loaded on form_obj
            active_assignments = FormAssignment.query.filter_by(form_id=form.id, is_deleted=False).all()


        if active_assignments:
            logger.debug(f"Form {form.id} has active assignments. Checking against user {user.id}.")
            for assignment in active_assignments:
                if assignment.entity_name == 'user' and assignment.entity_id == user.id:
                    logger.debug(f"Access granted for form {form.id} to user {user.id} via direct user assignment.")
                    return True
                if user.role_id and assignment.entity_name == 'role' and assignment.entity_id == user.role_id:
                    logger.debug(f"Access granted for form {form.id} to user {user.id} via role assignment (role ID: {user.role_id}).")
                    return True

                user_env_id = user.environment_id if hasattr(user, 'environment_id') else (user.environment.id if hasattr(user, 'environment') and user.environment else None)

                if user_env_id and assignment.entity_name == 'environment' and assignment.entity_id == user_env_id:
                    logger.debug(f"Access granted for form {form.id} to user {user.id} via environment assignment (env ID: {user_env_id}).")
                    return True
            logger.debug(f"Access denied for form {form.id} to user {user.id}. No matching assignments.")
            return False
        else: # No active assignments
            logger.debug(f"Form {form.id} has no active assignments. Applying default access rules for user {user.id}.")
            if hasattr(form, 'is_public') and form.is_public:
                logger.debug(f"Access granted for form {form.id} to user {user.id} because it's public and has no assignments.")
                return True

            form_creator = form.creator if hasattr(form, 'creator') and form.creator else (User.query.options(joinedload(User.environment)).get(form.user_id) if hasattr(form, 'user_id') else None)

            if form_creator and hasattr(form_creator, 'is_deleted') and not form_creator.is_deleted:
                creator_env_id = form_creator.environment_id if hasattr(form_creator, 'environment_id') else (form_creator.environment.id if hasattr(form_creator, 'environment') and form_creator.environment else None)
                user_env_id = user.environment_id if hasattr(user, 'environment_id') else (user.environment.id if hasattr(user, 'environment') and user.environment else None)

                if creator_env_id and user_env_id and creator_env_id == user_env_id:
                    logger.debug(f"Access granted for form {form.id} to user {user.id} (env ID: {user_env_id}) as it's in the creator's environment (env ID: {creator_env_id}) and has no assignments.")
                    return True

            logger.debug(f"Access denied for form {form.id} to user {user.id}. Not public, not creator, not in creator's environment (if applicable), and no assignments.")
            return False


    @staticmethod
    def get_accessible_forms_for_user(user_id: int) -> List[Form]:
        """
        Get all forms a user has access to, respecting the new assignment-based logic.
        """
        user = User.query.options(
            joinedload(User.role),
            joinedload(User.environment)
        ).filter_by(id=user_id, is_deleted=False).first()

        if not user:
            logger.warning(f"Cannot get accessible forms: User ID {user_id} not found or deleted.")
            return []

        if user.role and user.role.is_super_user:
            logger.debug(f"Admin user {user_id} retrieving all non-deleted forms.")
            return Form.query.options(
                joinedload(Form.creator).joinedload(User.environment),
                joinedload(Form.form_assignments) # Eager load assignments for efficiency in check_user_access_to_form
            ).filter_by(is_deleted=False).order_by(Form.title).all()

        # For non-admins, iterate through all forms and check access.
        # This can be optimized if performance becomes an issue for many forms.
        accessible_forms_dict = {}
        all_forms_to_check = Form.query.filter_by(is_deleted=False).options(
            joinedload(Form.creator).options(joinedload(User.role), joinedload(User.environment)),
            joinedload(Form.form_assignments) # Eager load assignments
        ).all()

        for form_item in all_forms_to_check:
            if form_item.id not in accessible_forms_dict:
                if FormAssignmentService.check_user_access_to_form(user_id, form_item.id, user_obj=user, form_obj=form_item):
                    accessible_forms_dict[form_item.id] = form_item

        accessible_forms_list = sorted(list(accessible_forms_dict.values()), key=lambda f: f.title if hasattr(f, 'title') else '')
        logger.info(f"User {user_id} has access to {len(accessible_forms_list)} forms.")
        return accessible_forms_list


    @staticmethod
    def delete_form_assignment(assignment_id: int) -> Tuple[bool, Optional[str]]:
        """Soft delete a form assignment."""
        try:
            assignment = FormAssignment.query.filter_by(id=assignment_id, is_deleted=False).first()
            if not assignment:
                return False, "Form assignment not found or already deleted."

            assignment.soft_delete()
            db.session.commit()
            logger.info(f"Form assignment ID {assignment_id} soft-deleted.")
            return True, "Form assignment deleted successfully."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting form assignment ID {assignment_id}: {str(e)}", exc_info=True)
            return False, f"An unexpected error occurred: {str(e)}"

    @staticmethod
    def get_assignments_batch_paginated(page: int, per_page: int, current_user: Optional[User] = None) -> Tuple[int, List[FormAssignment]]:
        """
        Get form assignments with pagination.
        If current_user is provided and is not an admin, filters to assignments of forms created by that user.
        """
        try:
            query = FormAssignment.query.options(
                joinedload(FormAssignment.form).joinedload(Form.creator)
            ).filter(FormAssignment.is_deleted == False)

            # --- MODIFICATION START: Filter by form ownership for non-admins ---
            if current_user and not (current_user.role and current_user.role.is_super_user):
                # Subquery to get IDs of forms owned by the current_user
                owned_form_ids_subquery = db.session.query(Form.id).filter(Form.user_id == current_user.id, Form.is_deleted == False)
                # Filter assignments where the form_id is in the list of owned_form_ids
                query = query.filter(FormAssignment.form_id.in_(owned_form_ids_subquery))
            # --- MODIFICATION END ---

            pagination_obj = query.order_by(FormAssignment.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )

            total_count = pagination_obj.total
            assignments = pagination_obj.items

            return total_count, assignments
        except Exception as e:
            logger.error(f"Error getting assignments batch paginated: {str(e)}", exc_info=True)
            return 0, []

    @staticmethod
    def get_all_assignments_unpaginated(current_user: Optional[User] = None) -> List[FormAssignment]:
        """
        Get ALL non-deleted form assignments.
        If current_user is provided and is not an admin, filters to assignments of forms created by that user.
        Use with caution due to potential performance impact on large datasets if no user or admin user.
        """
        try:
            query = FormAssignment.query.options(
                joinedload(FormAssignment.form).joinedload(Form.creator)
            ).filter(FormAssignment.is_deleted == False)

            # --- MODIFICATION START: Filter by form ownership for non-admins ---
            if current_user and not (current_user.role and current_user.role.is_super_user):
                owned_form_ids_subquery = db.session.query(Form.id).filter(Form.user_id == current_user.id, Form.is_deleted == False)
                query = query.filter(FormAssignment.form_id.in_(owned_form_ids_subquery))
            # --- MODIFICATION END ---

            return query.order_by(FormAssignment.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting all unpaginated assignments: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def update_form_assignment(assignment_id: int, update_data: Dict[str, Any]) -> Tuple[Optional[FormAssignment], Optional[str]]:
        """Update an existing form assignment (entity_name and/or entity_id)."""
        try:
            assignment = FormAssignment.query.filter_by(id=assignment_id, is_deleted=False).first()
            if not assignment:
                return None, "Form assignment not found or already deleted."

            new_entity_name = update_data.get('entity_name', assignment.entity_name)
            new_entity_id = update_data.get('entity_id', assignment.entity_id)

            if new_entity_name == assignment.entity_name and new_entity_id == assignment.entity_id:
                return assignment, "No changes detected." # Return the original assignment if no change

            is_valid_entity, entity_error = FormAssignmentService._validate_entity(new_entity_name, new_entity_id)
            if not is_valid_entity:
                return None, entity_error

            # Check if this exact assignment (form_id, new_entity_name, new_entity_id) already exists and is active
            existing_assignment_conflict = FormAssignment.query.filter(
                FormAssignment.form_id == assignment.form_id,
                FormAssignment.entity_name == new_entity_name,
                FormAssignment.entity_id == new_entity_id,
                FormAssignment.is_deleted == False,
                FormAssignment.id != assignment_id # Exclude the current assignment being updated
            ).first()

            if existing_assignment_conflict:
                return None, f"This form is already actively assigned to {new_entity_name} ID {new_entity_id} through another assignment record."

            assignment.entity_name = new_entity_name
            assignment.entity_id = new_entity_id

            db.session.commit()
            logger.info(f"Form assignment ID {assignment_id} updated to {new_entity_name}:{new_entity_id}.")
            # Eager load form and creator for the returned object to be consistent
            updated_assignment_with_relations = FormAssignment.query.options(
                joinedload(FormAssignment.form).joinedload(Form.creator)
            ).get(assignment_id) # Fetch again to get fresh data with eager loads
            return updated_assignment_with_relations, None

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error updating assignment ID {assignment_id}: {e}", exc_info=True)
            # Check for unique constraint violation specifically
            if hasattr(e, 'orig') and e.orig and ("UniqueViolation" in str(type(e.orig).__name__) or "_form_entity_uc" in str(e.orig)):
                return None, f"Database integrity error: This form is already assigned to the target entity (possibly due to a unique constraint on active assignments)."
            return None, "Database integrity error during update. Check for conflicts."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating assignment ID {assignment_id}: {e}", exc_info=True)
            return None, f"An unexpected error occurred during update: {str(e)}"