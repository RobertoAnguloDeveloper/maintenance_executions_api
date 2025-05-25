# app/views/form_assignment_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_assignment_controller import FormAssignmentController
from app.services.auth_service import AuthService # Assuming AuthService.get_current_user exists
from app.models.user import User # For type hinting
from app.utils.permission_manager import PermissionManager, EntityType, ActionType 
import logging

logger = logging.getLogger(__name__)
form_assignment_bp = Blueprint('form-assignments', __name__)

# Helper to get current user object (ensure this aligns with your AuthService)
def _get_auth_user() -> User:
    user_identity = get_jwt_identity() # This is usually the user's ID or a unique identifier
    # Assuming user_identity is the user_id directly or can be used to fetch the user
    user = AuthService.get_user_by_id(user_identity) # Or get_current_user(user_identity)
    if not user:
        # This case should ideally be handled by jwt_required if token is invalid/expired
        # If token is valid but user deleted, this is a valid scenario
        raise Exception("User not found for the provided token.") 
    return user

@form_assignment_bp.route('', methods=['POST'])
@jwt_required()
# Assuming 'update' on FORMS covers assigning/unassigning. Or create a specific 'assign' action.
@PermissionManager.require_permission(action=ActionType.UPDATE, entity_type=EntityType.FORMS)
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
        
        if not isinstance(form_id, int) or not isinstance(entity_id, int) or not isinstance(entity_name, str):
            return jsonify({"error": "Invalid data types for form_id, entity_name, or entity_id"}), 400


        assignment_dict, error = FormAssignmentController.create_form_assignment(
            form_id, entity_name, entity_id, current_user
        )
        if error:
            status_code = 400 # Default bad request
            if "not found" in error.lower(): status_code = 404
            elif "already assigned" in error.lower(): status_code = 409 # Conflict
            elif "unauthorized" in error.lower(): status_code = 403 # Forbidden
            return jsonify({"error": error}), status_code
        
        return jsonify({"message": "Form assigned successfully", "assignment": assignment_dict}), 201

    except Exception as e:
        logger.error(f"Error creating form assignment: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/bulk', methods=['POST'])
@jwt_required()
# Bulk operations might have stricter permissions, e.g., only admin or specific bulk_assign permission.
# For now, using the same as single assignment, but consider a more specific permission.
@PermissionManager.require_permission(action=ActionType.UPDATE, entity_type=EntityType.FORMS) # Or a new ActionType.BULK_ASSIGN
def create_bulk_assignments():
    """Bulk assign forms to entities."""
    try:
        current_user = _get_auth_user()
        assignments_data = request.get_json()

        if not isinstance(assignments_data, list):
            return jsonify({"error": "Invalid payload: Expected a list of assignment objects."}), 400
        if not assignments_data: # Empty list
             return jsonify({"error": "No assignment data provided in the list."}), 400


        results, error = FormAssignmentController.create_bulk_form_assignments(assignments_data, current_user)

        if error: # Errors at the controller level (e.g., authorization, top-level validation)
            status_code = 400
            if "unauthorized" in error.lower(): status_code = 403
            return jsonify({"error": error}), status_code
        
        # `results` from controller will be a dict: {"successful_assignments": [], "failed_assignments": []}
        # Determine appropriate status code based on results
        status_code = 207 # Multi-Status: some may have succeeded, some failed
        if results and not results.get("failed_assignments") and results.get("successful_assignments"):
            status_code = 201 # All created successfully
        elif results and not results.get("successful_assignments") and results.get("failed_assignments"):
            status_code = 400 # All failed, treat as a single bad request with details
        
        response_message = "Bulk assignment processing complete."
        if status_code == 201: response_message = "All assignments created successfully."
        elif status_code == 400 and results and not results.get("successful_assignments"):
            response_message = "All assignments failed to process."


        return jsonify({
            "message": response_message,
            "details": results # Contains successful_assignments and failed_assignments
        }), status_code

    except Exception as e:
        logger.error(f"Error in bulk creating form assignments: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS)
def get_assignments_for_a_form(form_id):
    """Get all assignments for a specific form."""
    try:
        current_user = _get_auth_user()
        assignments_list, error = FormAssignmentController.get_assignments_for_form(form_id, current_user)
        
        if error:
            status_code = 400
            if "not found" in error.lower(): status_code = 404
            elif "unauthorized" in error.lower(): status_code = 403
            return jsonify({"error": error}), status_code
            
        return jsonify({"form_id": form_id, "assignments": assignments_list}), 200
    except Exception as e:
        logger.error(f"Error getting assignments for form {form_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/entity/<string:entity_name>/<int:entity_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_forms_for_an_entity(entity_name, entity_id):
    """Get all forms assigned to a specific entity."""
    try:
        current_user = _get_auth_user()
        forms_list, error = FormAssignmentController.get_forms_for_entity(entity_name, entity_id, current_user)

        if error:
            status_code = 400
            if "unauthorized" in error.lower(): status_code = 403
            # Add specific error for invalid entity_name if service/controller provides it
            elif "invalid entity_name" in error.lower(): status_code = 400
            return jsonify({"error": error}), status_code
            
        return jsonify({"entity_name": entity_name, "entity_id": entity_id, "assigned_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting forms for entity {entity_name} {entity_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@form_assignment_bp.route('/user/accessible-forms', methods=['GET']) # Changed route for clarity
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_my_accessible_forms():
    """Get all forms accessible to the currently authenticated user."""
    try:
        current_user = _get_auth_user()
        # Controller method get_accessible_forms_for_user will handle if admin is trying to see for another user
        # but this endpoint is specifically for the logged-in user's forms.
        forms_list, error = FormAssignmentController.get_accessible_forms_for_user(current_user.id, current_user)
        
        if error: # Should be rare if current_user is always valid by this point
            status_code = 400
            if "unauthorized" in error.lower(): status_code = 403 # Should not happen for self
            return jsonify({"error": error}), status_code
            
        return jsonify({"user_id": current_user.id, "accessible_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting accessible forms for current user: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401 # Should be caught by _get_auth_user
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# If you need an admin endpoint to get forms for ANY user:
@form_assignment_bp.route('/user/<int:user_id>/accessible-forms', methods=['GET'])
@jwt_required()
# Changed ActionType.VIEW_ALL to ActionType.VIEW
# Admin-specific access is handled within the controller/service layers.
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_user_accessible_forms_admin(user_id):
    """(Admin) Get all forms accessible to a specific user."""
    try:
        current_user = _get_auth_user() # current_user is the admin performing the action
        
        # Authorization is handled by @PermissionManager and controller logic
        # The controller's get_accessible_forms_for_user already checks if current_user is admin
        # when current_user.id != user_id.

        forms_list, error = FormAssignmentController.get_accessible_forms_for_user(user_id, current_user)
        if error:
            status_code = 400
            if "unauthorized" in error.lower(): status_code = 403
            return jsonify({"error": error}), status_code
            
        return jsonify({"user_id": user_id, "accessible_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting accessible forms for user {user_id} by admin: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: Admin user not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/<int:assignment_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.UPDATE, entity_type=EntityType.FORMS) 
def delete_assignment(assignment_id):
    """Delete a specific form assignment."""
    try:
        current_user = _get_auth_user()
        success, error_or_message = FormAssignmentController.delete_form_assignment(assignment_id, current_user)
        
        if not success:
            status_code = 400
            if "not found" in str(error_or_message).lower(): status_code = 404
            elif "unauthorized" in str(error_or_message).lower(): status_code = 403
            return jsonify({"error": error_or_message}), status_code
        
        return jsonify({"message": error_or_message, "deleted_id": assignment_id}), 200 # message from service
    except Exception as e:
        logger.error(f"Error deleting form assignment {assignment_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
