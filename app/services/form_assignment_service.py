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
        if not model_class: # Should not happen if VALID_ENTITY_NAMES is correct
            logger.error(f"Internal error: No model class mapped for entity_name {entity_name}.")
            return False, f"Internal error: No model class mapped for entity_name {entity_name}."

        # Ensure entity is not soft-deleted
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
            # Ensure form is not soft-deleted
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, f"Form with ID {form_id} not found or is deleted."

            is_valid_entity, entity_error = FormAssignmentService._validate_entity(entity_name, entity_id)
            if not is_valid_entity:
                return None, entity_error

            # Check for existing non-deleted assignment
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
            # Check if it's a unique constraint violation (_form_entity_uc)
            if "UniqueViolation" in str(e.orig) or "_form_entity_uc" in str(e.orig):
                 return None, f"Database integrity error: This form is already assigned to {entity_name} ID {entity_id} (possibly soft-deleted but unique constraint still applies to non-deleted entries)."
            return None, "Database integrity error. Please check form/entity ID validity or potential unique constraint issues."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form assignment for form {form_id}, {entity_name} {entity_id}: {str(e)}", exc_info=True)
            return None, f"An unexpected error occurred: {str(e)}"

    @staticmethod
    def create_bulk_form_assignments(assignments_data: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Create multiple form assignments in bulk.
        Each item in assignments_data should be a dict with 'form_id', 'entity_name', 'entity_id'.
        """
        successful_assignments = []
        failed_assignments = []

        # Pre-fetch all relevant form IDs to reduce DB queries in loop
        # Ensure form_id exists and is an int before adding to set
        form_ids_to_check = list(set(
            item['form_id'] for item in assignments_data 
            if isinstance(item, dict) and isinstance(item.get('form_id'), int)
        ))
        valid_forms = {}
        if form_ids_to_check: # Only query if there are IDs to check
            valid_forms = {
                form.id: form for form in Form.query.filter(Form.id.in_(form_ids_to_check), Form.is_deleted == False).all()
            }
        
        # Pre-fetch entities could be done here similarly if performance becomes an issue
        # For now, validating entities one by one inside the loop.

        for item_data in assignments_data:
            # Ensure item_data is a dictionary before trying to get values
            if not isinstance(item_data, dict):
                failed_assignments.append({
                    "input": item_data, # item_data might not be a dict here
                    "error": "Invalid item format: Expected a dictionary."
                })
                continue

            form_id = item_data.get('form_id')
            entity_name = item_data.get('entity_name')
            entity_id = item_data.get('entity_id')
            
            original_input = {"form_id": form_id, "entity_name": entity_name, "entity_id": entity_id} # Store for error reporting

            # Basic payload validation for types
            if not (isinstance(form_id, int) and isinstance(entity_name, str) and isinstance(entity_id, int)):
                failed_assignments.append({
                    "input": original_input, # Use original_input which is now a dict
                    "error": "Invalid data types for form_id, entity_name, or entity_id."
                })
                continue
            
            # Check form existence and active status using pre-fetched data
            if form_id not in valid_forms:
                failed_assignments.append({
                    "input": original_input,
                    "error": f"Form with ID {form_id} not found or is deleted."
                })
                continue

            # Validate entity
            is_valid_entity, entity_error = FormAssignmentService._validate_entity(entity_name, entity_id)
            if not is_valid_entity:
                failed_assignments.append({
                    "input": original_input,
                    "error": entity_error
                })
                continue

            # Check for existing non-deleted assignment and create new one
            try: # Corrected: use colon instead of curly brace
                existing_assignment = FormAssignment.query.filter_by(
                    form_id=form_id,
                    entity_name=entity_name,
                    entity_id=entity_id,
                    is_deleted=False
                ).first()
                if existing_assignment:
                    failed_assignments.append({
                        "input": original_input,
                        "error": f"This form is already actively assigned to {entity_name} ID {entity_id}."
                    })
                    continue # Move to the next item in assignments_data

                new_assignment = FormAssignment(
                    form_id=form_id,
                    entity_name=entity_name,
                    entity_id=entity_id
                )
                db.session.add(new_assignment)
                # Add to a temporary list of models to be committed
                successful_assignments.append({"assignment_model": new_assignment, "input": original_input})

            except Exception as e: # Catch any unexpected error during individual processing for this item
                logger.error(f"Unexpected error during bulk processing for {original_input}: {str(e)}", exc_info=True)
                failed_assignments.append({
                    "input": original_input,
                    "error": f"An unexpected error occurred while processing this item: {str(e)}"
                })
                # Continue to the next item even if one fails here before the commit stage
        
        # Attempt to commit all successfully prepared new assignments
        processed_successful_for_return = []
        if successful_assignments: # Only attempt commit if there's something to commit
            try:
                db.session.commit()
                for success_item_info in successful_assignments:
                    # Access ID after commit
                    processed_successful_for_return.append({
                        "form_id": success_item_info["input"]["form_id"],
                        "entity_name": success_item_info["input"]["entity_name"],
                        "entity_id": success_item_info["input"]["entity_id"],
                        "assignment_id": success_item_info["assignment_model"].id 
                    })
                    logger.info(f"Bulk: Form {success_item_info['input']['form_id']} assigned to {success_item_info['input']['entity_name']} ID {success_item_info['input']['entity_id']}. Assignment ID: {success_item_info['assignment_model'].id}")
            except IntegrityError as e:
                db.session.rollback()
                logger.error(f"Integrity error during bulk commit: {e}", exc_info=True)
                # This case is complex: some items that passed individual checks might have violated constraints
                # (e.g. due to data changes between check and commit, or complex multi-item constraints).
                # Move all items from successful_assignments (that were pending commit) to failed_assignments.
                for pending_success_item in successful_assignments:
                     failed_assignments.append({
                        "input": pending_success_item["input"],
                        "error": "Database integrity error during bulk commit. The assignment might conflict with an existing one or violate other constraints."
                    })
                processed_successful_for_return = [] # Clear as the commit failed
            except Exception as e:
                db.session.rollback()
                logger.error(f"Generic error during bulk commit: {e}", exc_info=True)
                for pending_success_item in successful_assignments:
                     failed_assignments.append({
                        "input": pending_success_item["input"],
                        "error": f"An unexpected error occurred during bulk commit: {str(e)}"
                    })
                processed_successful_for_return = [] # Clear as the commit failed

        return {
            "successful_assignments": processed_successful_for_return,
            "failed_assignments": failed_assignments
        }

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
    def check_user_access_to_form(user_id: int, form_id: int, user_obj: Optional[User] = None, form_obj: Optional[Form] = None) -> bool:
        """
        Check if a user has access to a specific form based on new assignment rules.
        Can accept pre-fetched user_obj and form_obj for optimization.
        """
        # Fetch user if not provided or if provided user is deleted
        if user_obj is None or (hasattr(user_obj, 'is_deleted') and user_obj.is_deleted):
            user = User.query.options(joinedload(User.role)).filter_by(id=user_id, is_deleted=False).first()
        else:
            user = user_obj
        
        if not user:
            logger.warning(f"Access check failed: User ID {user_id} not found or deleted.")
            return False

        # Fetch form if not provided or if provided form is deleted
        if form_obj is None or (hasattr(form_obj, 'is_deleted') and form_obj.is_deleted):
            form = Form.query.options(joinedload(Form.creator)).filter_by(id=form_id, is_deleted=False).first()
        else:
            form = form_obj

        if not form:
            logger.warning(f"Access check failed: Form ID {form_id} not found or deleted.")
            return False
        
        # 1. Admin Override
        if user.role and user.role.is_super_user:
            logger.debug(f"Access granted for form {form.id} to admin user {user.id}.")
            return True

        # 2. Creator Override
        if form.user_id == user.id:
            logger.debug(f"Access granted for form {form.id} to creator user {user.id}.")
            return True

        # 3. Fetch active assignments for the form (can be optimized if form_obj has them preloaded)
        # Ensure form.form_assignments is accessed safely if it might not exist or be None
        active_assignments = []
        if hasattr(form, 'form_assignments') and form.form_assignments is not None:
            active_assignments = [assign for assign in form.form_assignments if hasattr(assign, 'is_deleted') and not assign.is_deleted]
        else: # Fetch if not preloaded or if attribute doesn't exist
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
                # Assuming user model has environment_id. If not, this needs adjustment.
                if hasattr(user, 'environment_id') and user.environment_id and \
                   assignment.entity_name == 'environment' and assignment.entity_id == user.environment_id:
                    logger.debug(f"Access granted for form {form.id} to user {user.id} via environment assignment (env ID: {user.environment_id}).")
                    return True
            logger.debug(f"Access denied for form {form.id} to user {user.id}. No matching assignments.")
            return False 
        else:
            logger.debug(f"Form {form.id} has no active assignments. Applying default access rules for user {user.id}.")
            # 4. Public Form (if no assignments)
            if hasattr(form, 'is_public') and form.is_public:
                logger.debug(f"Access granted for form {form.id} to user {user.id} because it's public and has no assignments.")
                return True
            
            # 5. Same Environment as Creator (if no assignments and not public)
            form_creator = None
            if hasattr(form, 'creator') and form.creator: # Assumes creator is loaded
                form_creator = form.creator
            elif hasattr(form, 'user_id'): # Fallback if creator relationship not loaded
                 form_creator = User.query.get(form.user_id) # Potential N+1 if not careful

            if form_creator and hasattr(form_creator, 'is_deleted') and not form_creator.is_deleted and \
               hasattr(form_creator, 'environment_id') and form_creator.environment_id and \
               hasattr(user, 'environment_id') and user.environment_id and \
               form_creator.environment_id == user.environment_id:
                logger.debug(f"Access granted for form {form.id} to user {user.id} (env ID: {user.environment_id}) as it's in the creator's environment (env ID: {form_creator.environment_id}) and has no assignments.")
                return True
            
            logger.debug(f"Access denied for form {form.id} to user {user.id}. Not public, not in creator's environment, and no assignments.")
            return False

    @staticmethod
    def get_accessible_forms_for_user(user_id: int) -> List[Form]:
        """
        Get all forms a user has access to, respecting the new assignment-based logic.
        """
        user = User.query.options(
            joinedload(User.role), 
            # joinedload(User.environment) # If User model has direct environment relationship and it's needed
        ).filter_by(id=user_id, is_deleted=False).first()

        if not user:
            logger.warning(f"Cannot get accessible forms: User ID {user_id} not found or deleted.")
            return []

        if user.role and user.role.is_super_user:
            logger.debug(f"Admin user {user_id} retrieving all non-deleted forms.")
            return Form.query.filter_by(is_deleted=False).order_by(Form.title).all()

        accessible_forms_dict = {} # Use dict to avoid duplicates if accessible through multiple paths

        # Eager load necessary relationships for forms to optimize checks
        all_forms_to_check = Form.query.filter_by(is_deleted=False).options(
            joinedload(Form.creator).options(joinedload(User.role), joinedload(User.environment.name)), # Eager load creator's role and environment name if user has environment
            joinedload(Form.form_assignments) # Eager load assignments for checks
        ).all()

        for form_item in all_forms_to_check:
            if form_item.id not in accessible_forms_dict: # Check only if not already added
                # Pass pre-fetched user and form objects for optimization
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