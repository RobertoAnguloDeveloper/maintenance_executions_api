# app/views/form_assignment_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_assignment_controller import FormAssignmentController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType # Assuming FORMS permission covers assignments
import logging

logger = logging.getLogger(__name__)
form_assignment_bp = Blueprint('form-assignments', __name__)

# Helper to get current user object
def _get_auth_user():
    user_identity = get_jwt_identity()
    user = AuthService.get_current_user(user_identity)
    if not user:
        raise Exception("User not found or token invalid") # Will be caught by try-except
    return user

@form_assignment_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS) # Or a new 'assign' action
def create_assignment():
    """Assign a form to an entity (user, role, or environment)."""
    try:
        current_user = _get_auth_user()
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        form_id = data.get('form_id')
        entity_name = data.get('entity_name')
        entity_id = data.get('entity_id')

        if not all([form_id, entity_name, entity_id]):
            return jsonify({"error": "Missing required fields: form_id, entity_name, entity_id"}), 400
        
        # Authorization: Typically, only the form owner or an admin should be able to assign forms.
        # This can be more granularly handled in the controller or service.
        # For now, relying on the require_permission for FORMS update.

        assignment_dict, error = FormAssignmentController.create_form_assignment(form_id, entity_name, entity_id, current_user)
        if error:
            status_code = 400
            if "not found" in error.lower(): status_code = 404
            elif "already assigned" in error.lower(): status_code = 409 # Conflict
            return jsonify({"error": error}), status_code
        
        return jsonify({"message": "Form assigned successfully", "assignment": assignment_dict}), 201

    except Exception as e:
        logger.error(f"Error creating form assignment: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": str(e)}), 401
        return jsonify({"error": "Internal server error"}), 500

@form_assignment_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_assignments_for_a_form(form_id):
    """Get all assignments for a specific form."""
    try:
        current_user = _get_auth_user()
        # Authorization: Form owner or admin can see assignments.
        # This check could also be in the controller/service.
        assignments_list, error = FormAssignmentController.get_assignments_for_form(form_id, current_user)
        if error: # Should not happen if controller handles it, but good for safety
            return jsonify({"error": error}), 400
            
        return jsonify({"form_id": form_id, "assignments": assignments_list}), 200
    except Exception as e:
        logger.error(f"Error getting assignments for form {form_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": str(e)}), 401
        return jsonify({"error": "Internal server error"}), 500


@form_assignment_bp.route('/entity/<string:entity_name>/<int:entity_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS) # User needs to see forms
def get_forms_for_an_entity(entity_name, entity_id):
    """Get all forms assigned to a specific entity."""
    try:
        current_user = _get_auth_user()
        # Authorization: Depending on the entity, might restrict who can see this.
        # E.g., if entity_name is 'user', only that user or admin.
        forms_list, error = FormAssignmentController.get_forms_for_entity(entity_name, entity_id, current_user)
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({"entity_name": entity_name, "entity_id": entity_id, "assigned_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting forms for entity {entity_name} {entity_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": str(e)}), 401
        return jsonify({"error": "Internal server error"}), 500

@form_assignment_bp.route('/user/<int:user_id>/accessible-forms', methods=['GET'])
@jwt_required()
# Permission can be tricky here: user viewing their own, or admin viewing for others.
# The controller/service should handle this.
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS) 
def get_user_accessible_forms(user_id):
    """Get all forms accessible to a specific user."""
    try:
        current_user = _get_auth_user()
        
        # Authorization: User can request their own forms. Admin can request for any user.
        if current_user.id != user_id and not current_user.role.is_super_user:
            return jsonify({"error": "Unauthorized to view accessible forms for this user."}), 403
            
        forms_list, error = FormAssignmentController.get_accessible_forms_for_user(user_id, current_user)
        if error:
            return jsonify({"error": error}), 400 # Controller should return more specific codes if possible
            
        return jsonify({"user_id": user_id, "accessible_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting accessible forms for user {user_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": str(e)}), 401
        return jsonify({"error": "Internal server error"}), 500


@form_assignment_bp.route('/<int:assignment_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS) # Or a new 'unassign' action
def delete_assignment(assignment_id):
    """Delete a specific form assignment."""
    try:
        current_user = _get_auth_user()
        # Authorization: Similar to creation, typically form owner or admin.
        # This can be enforced in the controller/service.
        success, error_or_message = FormAssignmentController.delete_form_assignment(assignment_id, current_user)
        if not success:
            status_code = 400
            if "not found" in str(error_or_message).lower(): status_code = 404
            return jsonify({"error": error_or_message}), status_code
        
        return jsonify({"message": "Form assignment deleted successfully", "deleted_id": assignment_id}), 200
    except Exception as e:
        logger.error(f"Error deleting form assignment {assignment_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": str(e)}), 401
        return jsonify({"error": "Internal server error"}), 500