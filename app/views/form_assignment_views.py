# app/views/form_assignment_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_assignment_controller import FormAssignmentController
from app.services.auth_service import AuthService 
from app.models.user import User 
from app.services.form_assignment_service import FormAssignmentService
from app.utils.permission_manager import PermissionManager, EntityType, ActionType 
import logging

logger = logging.getLogger(__name__)
form_assignment_bp = Blueprint('form-assignments', __name__)

def _get_auth_user() -> User:
    user_identity = get_jwt_identity() 
    user = AuthService.get_user_by_id(user_identity) if isinstance(user_identity, int) else AuthService.get_current_user(str(user_identity))
    if not user:
        raise Exception("User not found for the provided token.") 
    return user

@form_assignment_bp.route('', methods=['POST'])
@jwt_required()
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

        if not (isinstance(form_id, int) and 
                isinstance(entity_name, str) and entity_name.strip() and 
                isinstance(entity_id, int)):
            return jsonify({"error": "Invalid data types or missing required fields: form_id (int), entity_name (non-empty str), entity_id (int)"}), 400

        assignment_dict, error = FormAssignmentController.create_form_assignment(
            form_id, entity_name, entity_id, current_user
        )
        if error:
            status_code = 400 
            if "not found" in error.lower(): status_code = 404
            elif "already assigned" in error.lower(): status_code = 409 
            elif "unauthorized" in error.lower(): status_code = 403 
            return jsonify({"error": error}), status_code
        
        return jsonify({"message": "Form assigned successfully", "assignment": assignment_dict}), 201

    except Exception as e:
        logger.error(f"Error creating form assignment: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.UPDATE, entity_type=EntityType.FORMS) 
def create_bulk_assignments():
    """Bulk assign forms to entities."""
    try:
        current_user = _get_auth_user()
        assignments_data = request.get_json()

        if not isinstance(assignments_data, list):
            return jsonify({"error": "Invalid payload: Expected a list of assignment objects."}), 400
        if not assignments_data: 
             return jsonify({"error": "No assignment data provided in the list."}), 400


        results, error = FormAssignmentController.create_bulk_form_assignments(assignments_data, current_user)

        if error: 
            status_code = 400
            if "unauthorized" in error.lower(): status_code = 403
            return jsonify({"error": error}), status_code
        
        status_code = 207 
        if results and not results.get("failed_assignments") and results.get("successful_assignments"):
            status_code = 201 
        elif results and not results.get("successful_assignments") and results.get("failed_assignments"):
            status_code = 400 
        
        response_message = "Bulk assignment processing complete."
        if status_code == 201: response_message = "All assignments created successfully."
        elif status_code == 400 and results and not results.get("successful_assignments"): 
            response_message = "All assignments failed to process."


        return jsonify({
            "message": response_message,
            "details": results 
        }), status_code

    except Exception as e:
        logger.error(f"Error in bulk creating form assignments: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@form_assignment_bp.route('/batch', methods=['GET']) # Changed from '' to '/batch'
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_assignments_batch_view(): # Renamed function
    """
    Get form assignments in a paginated batch. Admin-only.
    """
    try:
        current_user = _get_auth_user()
        
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)

        result, error = FormAssignmentController.get_assignments_batch(page, per_page, current_user) # Updated controller call

        if error:
            status_code = 403 if "unauthorized" in error.lower() else 500
            return jsonify({"error": error}), status_code

        total_count, assignments_list = result
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
        
        current_page_display = page
        if total_pages > 0 and page > total_pages: 
            current_page_display = total_pages
        elif page < 1 and total_pages > 0 : 
            current_page_display = 1
        elif total_pages == 0 and page >= 1: 
             current_page_display = 1


        return jsonify({
            "metadata": {
                "total_items": total_count,
                "total_pages": total_pages,
                "current_page": current_page_display,
                "per_page": per_page,
            },
            "assignments": assignments_list
        }), 200

    except Exception as e:
        logger.error(f"Error getting assignments batch: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@form_assignment_bp.route('', methods=['GET']) # New endpoint for unpaginated results
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_all_assignments_unpaginated_view(): # New view function
    """
    Get ALL form assignments (unpaginated). Admin-only.
    Use with caution for large datasets.
    """
    try:
        current_user = _get_auth_user()
        assignments_list, error = FormAssignmentController.get_all_assignments_unpaginated_controller(current_user)

        if error:
            status_code = 403 if "unauthorized" in error.lower() else 500
            return jsonify({"error": error}), status_code
        
        return jsonify({"assignments": assignments_list, "total_items": len(assignments_list)}), 200

    except Exception as e:
        logger.error(f"Error getting all unpaginated assignments: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/<int:assignment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS)
def get_assignment(assignment_id):
    """Get a specific form assignment."""
    try:
        current_user = _get_auth_user()
        
        assignment = FormAssignmentService.get_form_assignment_by_id(assignment_id)
        if not assignment:
            return jsonify({"error": "Form assignment not found"}), 404

        if not FormAssignmentService.check_user_access_to_form(current_user.id, assignment.form_id, user_obj=current_user, form_obj=assignment.form):
             return jsonify({"error": "Access to this form assignment is denied"}), 403

        return jsonify(assignment.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting form assignment {assignment_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": "Internal server error"}), 500

@form_assignment_bp.route('/<int:assignment_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.UPDATE, entity_type=EntityType.FORMS)
def update_assignment(assignment_id):
    """Update an existing form assignment (e.g., change entity_id)."""
    try:
        current_user = _get_auth_user()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No update data provided"}), 400

        update_payload = {}
        if 'entity_name' in data:
            if not isinstance(data['entity_name'], str) or not data['entity_name'].strip():
                return jsonify({"error": "Invalid entity_name: Must be a non-empty string"}), 400
            update_payload['entity_name'] = data['entity_name']
        
        if 'entity_id' in data:
            if not isinstance(data['entity_id'], int):
                return jsonify({"error": "Invalid entity_id: Must be an integer"}), 400
            update_payload['entity_id'] = data['entity_id']

        if not update_payload:
            return jsonify({"error": "No valid fields (entity_name, entity_id) provided for update."}), 400

        updated_assignment_dict, error = FormAssignmentController.update_form_assignment(
            assignment_id, update_payload, current_user
        )

        if error:
            status_code = 400 
            if "not found" in error.lower(): status_code = 404
            elif "already assigned" in error.lower() or "conflict" in error.lower(): status_code = 409 
            elif "unauthorized" in error.lower(): status_code = 403 
            return jsonify({"error": error}), status_code

        return jsonify({
            "message": "Form assignment updated successfully",
            "assignment": updated_assignment_dict
        }), 200

    except Exception as e:
        logger.error(f"Error updating form assignment {assignment_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
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
        
        return jsonify({"message": error_or_message, "deleted_id": assignment_id}), 200 
    except Exception as e:
        logger.error(f"Error deleting form assignment {assignment_id}: {str(e)}", exc_info=True)
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
            elif "invalid entity_name" in error.lower(): status_code = 400 
            return jsonify({"error": error}), status_code
            
        return jsonify({"entity_name": entity_name, "entity_id": entity_id, "assigned_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting forms for entity {entity_name} {entity_id}: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@form_assignment_bp.route('/user/accessible-forms', methods=['GET']) 
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_my_accessible_forms():
    """Get all forms accessible to the currently authenticated user."""
    try:
        current_user = _get_auth_user()
        forms_list, error = FormAssignmentController.get_accessible_forms_for_user(current_user.id, current_user)
        
        if error: 
            status_code = 400
            if "unauthorized" in error.lower(): status_code = 403 
            return jsonify({"error": error}), status_code
            
        return jsonify({"user_id": current_user.id, "accessible_forms": forms_list}), 200
    except Exception as e:
        logger.error(f"Error getting accessible forms for current user: {str(e)}", exc_info=True)
        if "User not found" in str(e): return jsonify({"error": "Authentication error: User not found."}), 401 
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@form_assignment_bp.route('/user/<int:user_id>/accessible-forms', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.FORMS) 
def get_user_accessible_forms_admin(user_id):
    """(Admin) Get all forms accessible to a specific user."""
    try:
        current_user = _get_auth_user() 
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