# app/views/form_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_controller import FormController
from app.controllers.user_controller import UserController # For validating user_id if creating for others
from app.services.auth_service import AuthService # For getting current user object
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
from app.services.form_assignment_service import FormAssignmentService # For checking form access if needed
import logging

logger = logging.getLogger(__name__)
form_bp = Blueprint('forms', __name__)

@form_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_form():
    """
    Create a new form.
    Accepts 'title', 'description' (optional), 'is_public' (optional, default False),
    'attachments_required' (optional, default False), and 'user_id' (optional, admin only).
    """
    try:
        data = request.get_json()
        current_user_identity = get_jwt_identity() # Get username from token

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['title']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields (title is required)"}), 400

        current_user_obj = AuthService.get_current_user(current_user_identity)
        if not current_user_obj:
            logger.error(f"Current user not found: {current_user_identity}")
            return jsonify({"error": "Authentication error"}), 401

        user_id_for_form = current_user_obj.id # Default to current user

        if 'user_id' in data and data['user_id'] != current_user_obj.id:
            if not current_user_obj.role.is_super_user:
                return jsonify({"error": "Permission denied to create forms for other users"}), 403

            target_user = UserController.get_user(data['user_id'])
            if not target_user:
                 return jsonify({"error": f"User with ID {data['user_id']} not found."}), 404
            user_id_for_form = data['user_id']

        new_form, error = FormController.create_form(
            title=data['title'],
            description=data.get('description'),
            user_id=user_id_for_form,
            is_public=data.get('is_public', False),
            attachments_required=data.get('attachments_required', False) # Pass new field
        )

        if error:
            logger.error(f"Error creating form: {error}")
            status_code = 400
            if "already exists" in error.lower():
                status_code = 409 # Conflict
            return jsonify({"error": error}), status_code

        logger.info(f"Form '{new_form.title}' created successfully by user {current_user_identity}")
        # The controller returns the form model instance if successful
        return jsonify({
            "message": "Form created successfully",
            "form": new_form.to_dict(),
        }), 201

    except Exception as e:
        logger.error(f"Error in create_form view: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_all_forms():
    """
    Get all forms accessible to the current user (full details).
    Uses FormAssignmentService for comprehensive access check.
    """
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        # FormController.get_all_forms will internally use FormAssignmentService
        accessible_forms = FormController.get_all_forms(user)

        response_data = [form.to_dict() for form in accessible_forms] # Full dict

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting forms: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/compact', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_all_forms_compact_view(): # Was get_all_forms_basic in earlier context, ensure correct name
    """
    Get compact information for all forms accessible to the current user.
    Returns: id, title, description, questions_count, created_at, updated_at, created_by_fullname.
    
    Query Parameters:
        - date_filter_field (str): Field to filter by date ('created_at' or 'updated_at').
        - start_date (str): Start date for filtering (ISO format).
        - end_date (str): End date for filtering (ISO format).
        - sort_by (str): Field to sort by ('updated_at', 'title', 'created_at'). Default: 'updated_at'.
        - sort_order (str): Sort order ('asc' or 'desc'). Default: 'desc'.
        - only_editable (str): 'true' or 'false'. If 'true', returns only forms editable by the current user. Default: 'false'.
    """
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user:
            return jsonify({"error": "User not found"}), 401

        # Get filter and sort parameters from request arguments
        date_filter_field = request.args.get('date_filter_field')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        sort_by = request.args.get('sort_by', default='updated_at')
        sort_order = request.args.get('sort_order', default='desc').lower()
        
        only_editable_str = request.args.get('only_editable', 'false').lower()
        only_editable = only_editable_str == 'true' # Convert to boolean

        # Validate sort_order
        if sort_order not in ['asc', 'desc']:
            return jsonify({"error": "Invalid sort_order. Must be 'asc' or 'desc'."}), 400
        
        # Validate sort_by
        valid_sort_fields = ['updated_at', 'title', 'created_at']
        if sort_by not in valid_sort_fields:
            return jsonify({"error": f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"}), 400

        # Validate date_filter_field if provided
        if date_filter_field and date_filter_field not in ['created_at', 'updated_at']:
             return jsonify({"error": "Invalid date_filter_field. Must be 'created_at' or 'updated_at'."}), 400
        
        # Basic validation for date presence if field is specified
        if date_filter_field and (not start_date_str or not end_date_str):
            return jsonify({"error": "start_date and end_date are required if date_filter_field is specified."}), 400
        
        forms_compact_info, error = FormController.get_all_forms_compact_controller(
            current_user=user, # Pass the User object
            date_filter_field=date_filter_field,
            start_date=start_date_str, 
            end_date=end_date_str,     
            sort_by=sort_by,
            sort_order=sort_order,
            only_editable=only_editable # Pass the new boolean parameter
        )
        
        if error:
            return jsonify({"error": error}), 500 

        return jsonify(forms_compact_info), 200

    except Exception as e:
        logger.error(f"Error in get_all_forms_compact_view: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/batch', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_batch_forms():
    """
    Get batch of forms with pagination. Access control is handled by FormService.get_batch.
    """
    try:
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)

        include_deleted_str = request.args.get('include_deleted', 'false').lower()
        include_deleted = include_deleted_str == 'true'

        is_public_str = request.args.get('is_public')
        is_public = None
        if is_public_str is not None:
            is_public = is_public_str.lower() == 'true'

        user_id_filter = request.args.get('user_id', type=int)
        environment_id_filter = request.args.get('environment_id', type=int)

        only_editable_str = request.args.get('only_editable', 'false').lower()
        only_editable = only_editable_str == 'true'

        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        filters = {
            'include_deleted': include_deleted,
            'is_public': is_public,
            'user_id': user_id_filter,
            'environment_id': environment_id_filter,
            'current_user': user, # Pass the user object for role-based filtering in service
            'only_editable': only_editable
        }

        # Remove None filters to avoid passing them if not specified
        filters = {k: v for k, v in filters.items() if v is not None or k == 'is_public'}


        total_count, forms_data = FormController.get_batch(page=page, per_page=per_page, **filters)

        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0

        return jsonify({
            "metadata": {
                "total_items": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": per_page,
            },
            "items": forms_data # Service already returns dicts
        }), 200

    except Exception as e:
        logger.error(f"Error getting batch of forms: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@form_bp.route('/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_form(form_id):
    """Get a specific form if the user has access."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        # Check access using FormAssignmentService
        if not FormAssignmentService.check_user_access_to_form(user.id, form_id):
            return jsonify({"error": "Access to this form is denied"}), 403

        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404

        return jsonify(form.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/environment/<int:environment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_forms_by_environment(environment_id):
    """Get all forms associated with an environment, if user has access."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        # Authorization check: User must be superuser OR belong to the requested environment.
        # This check is now also implicitly handled by the service, but keeping it here provides
        # an early exit and a specific error message.
        if not user.role.is_super_user and user.environment_id != environment_id:
            logger.warning(f"User {user.username} (env: {user.environment_id}) attempted to access forms for env {environment_id}.")
            return jsonify({"error": "Unauthorized to access forms for this environment"}), 403

        forms = FormController.get_forms_by_environment(environment_id, user)

        forms_data = [form.to_dict() for form in forms if hasattr(form, 'to_dict')]
        logger.info(f"Found {len(forms_data)} forms for environment {environment_id}")

        return jsonify({"forms": forms_data}), 200

    except Exception as e:
        logger.error(f"Error getting forms by environment {environment_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/public', methods=['GET'])
@jwt_required() # Still require auth to see public forms, as per original design
def get_public_forms():
    """Get all public forms."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        forms = FormController.get_public_forms(user)
        if forms is None: # Should not happen if controller returns [] on error
            return jsonify([]), 200

        forms_data = [form.to_dict() for form in forms if hasattr(form, 'to_dict')]
        return jsonify(forms_data), 200

    except Exception as e:
        logger.error(f"Error getting public forms: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/creator/<string:username>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_forms_by_creator(username: str):
    """Get all forms created by a specific username, respecting current user's access."""
    try:
        current_user_identity = get_jwt_identity()
        requesting_user = AuthService.get_current_user(current_user_identity)
        if not requesting_user: return jsonify({"error": "User not found"}), 401

        forms = FormController.get_forms_by_creator(username, requesting_user)

        if forms is None: # Service/Controller might return None if creator not found
            return jsonify({"error": f"Creator '{username}' not found or error retrieving forms"}), 404

        # The service layer now handles the access check, so we can directly convert.
        forms_data = [form_model.to_dict() for form_model in forms]

        return jsonify(forms_data), 200

    except Exception as e:
        logger.error(f"Error getting forms by creator {username}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@form_bp.route('/<int:form_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS)
def update_form(form_id):
    """Update a form's details, including 'attachments_required'."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        form_to_update = FormController.get_form(form_id) # Returns a Form model instance
        if not form_to_update:
            return jsonify({"error": "Form not found"}), 404

        # Authorization: Only form creator or admin can update
        if form_to_update.user_id != user.id and not user.role.is_super_user:
            return jsonify({"error": "Unauthorized to update this form"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        allowed_update_fields = ['title', 'description', 'is_public', 'attachments_required']
        update_payload = {k: v for k, v in data.items() if k in allowed_update_fields}

        if not update_payload:
            return jsonify({"error": "No valid fields provided for update"}), 400

        if 'is_public' in update_payload and update_payload['is_public'] and user.role.name == RoleType.SUPERVISOR:
             return jsonify({"error": "Supervisors cannot make forms public"}), 403

        result_dict = FormController.update_form(form_id, **update_payload) # Controller returns a dict

        if "error" in result_dict:
            status_code = 400
            if "not found" in result_dict["error"].lower(): status_code = 404
            elif "already exists" in result_dict["error"].lower(): status_code = 409
            return jsonify({"error": result_dict["error"]}), status_code

        logger.info(f"Form {form_id} updated successfully by user {user.username}")
        return jsonify(result_dict), 200

    except Exception as e:
        logger.error(f"Error updating form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/<int:form_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.FORMS)
def delete_form(form_id):
    """Delete a form (soft delete)."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        form_to_delete = FormController.get_form(form_id) # Returns a Form model instance
        if not form_to_delete:
            return jsonify({"error": "Form not found"}), 404

        # Authorization: Only form creator or admin can delete
        if form_to_delete.user_id != user.id and not user.role.is_super_user:
            return jsonify({"error": "Unauthorized to delete this form"}), 403

        success, result_or_error = FormController.delete_form(form_id, user)

        if success:
            logger.info(f"Form {form_id} and associated data deleted by {user.username}")
            return jsonify({
                "message": "Form and associated data deleted successfully",
                "deleted_items_summary": result_or_error # result_or_error is the stats dict here
            }), 200

        return jsonify({"error": result_or_error}), 400 # result_or_error is the error string here

    except Exception as e:
        logger.error(f"Error deleting form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# --- Endpoints related to questions within a form ---
@form_bp.route('/<int:form_id>/questions', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS) # Updating a form by adding questions
def add_questions_to_form(form_id):
    """Add new questions to an existing form."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        form_to_update = FormController.get_form(form_id)
        if not form_to_update:
            return jsonify({"error": "Form not found"}), 404

        if form_to_update.user_id != user.id and not user.role.is_super_user:
            return jsonify({"error": "Unauthorized to add questions to this form"}), 403

        data = request.get_json()
        if 'questions' not in data or not isinstance(data['questions'], list):
            return jsonify({"error": "Questions list is required"}), 400

        # The FormController.add_questions_to_form is not defined in the provided files.
        # Assuming it would call FormService.add_questions_to_form
        from app.services.form_service import FormService # Local import if not at top
        updated_form, error = FormService.add_questions_to_form(
            form_id=form_id,
            questions=data['questions']
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Questions added to form {form_id} by user {user.username}")
        return jsonify({
            "message": "Questions added successfully",
            "form": updated_form.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error adding questions to form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# --- Endpoints related to submissions for a form ---
@form_bp.route('/<int:form_id>/submissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS) # Viewing submissions
def get_form_submissions(form_id):
    """Get all submissions for a specific form, respecting user access."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        # Check if user can view the form itself first
        if not FormAssignmentService.check_user_access_to_form(user.id, form_id):
             return jsonify({"error": "Access to this form's submissions is denied"}), 403

        form = FormController.get_form(form_id)
        if not form: # Should be caught by check_user_access_to_form if form doesn't exist
            return jsonify({"error": "Form not found"}), 404

        submissions_list, error = FormController.get_form_submissions(form_id, user)

        if error: # Should not happen if controller handles it
            return jsonify({"error": error}), 500

        return jsonify(submissions_list), 200

    except Exception as e:
        logger.error(f"Error getting submissions for form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# --- Endpoint for form statistics ---
@form_bp.route('/<int:form_id>/statistics', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS) # Viewing form stats
def get_form_statistics(form_id):
    """Get statistics for a specific form."""
    try:
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user: return jsonify({"error": "User not found"}), 401

        # Check if user can view the form itself first
        if not FormAssignmentService.check_user_access_to_form(user.id, form_id):
             return jsonify({"error": "Access to this form's statistics is denied"}), 403

        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404

        # Technicians typically shouldn't access aggregate statistics (Handled in service, but early exit is fine)
        if user.role.name == RoleType.TECHNICIAN:
            return jsonify({"error": "Unauthorized to view form statistics"}), 403

        stats, error = FormController.get_form_statistics(form_id, user)
        if error:
            return jsonify({"error": error}), 400 # Or 500 depending on error nature

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting statistics for form {form_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
