# app/views/report_template_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.report_template_controller import ReportTemplateController
from app.services.auth_service import AuthService
# Import PermissionManager and RoleType if you want to use permission decorators
from app.utils.permission_manager import PermissionManager, RoleType
import logging

# Get the logger instance configured in app/__init__.py
logger = logging.getLogger("app")

# Create a Blueprint for report template endpoints
# All routes defined here will be prefixed with /api/v1/report-templates
report_template_bp = Blueprint('report_templates', __name__)

# --- Helper Function ---
def _get_current_user():
    """
    Helper function to retrieve the currently authenticated user object.
    Handles JWT identity fetching and user lookup.
    Returns the user object or None and an error tuple (message, status_code).
    """
    try:
        user_identity = get_jwt_identity()
        if not user_identity:
             logger.warning("Attempted access to template endpoint without JWT identity.")
             return None, ({"error": "Authentication required"}, 401)

        user = AuthService.get_current_user(user_identity)
        if not user:
            # Log warning and prepare error response components
            logger.warning(f"Invalid user identity '{user_identity}' accessed template endpoint.")
            return None, ({"error": "Invalid user or token"}, 401) # Unauthorized
        return user, None
    except Exception as e:
        logger.exception(f"Error retrieving current user in template views: {e}")
        return None, ({"error": "Internal server error during authentication"}, 500)


# --- Routes ---

@report_template_bp.route('/', methods=['POST'])
@jwt_required()
# Optional: Add role/permission check decorator if needed.
# Example: Allow Admins and Site Managers to create templates
# @PermissionManager.require_role(RoleType.ADMIN, RoleType.SITE_MANAGER)
def create_report_template():
    """
    API endpoint to create a new report template.
    Requires JWT authentication.
    Expects JSON body with: name (str, required), form_id (int, required), configuration (dict, required),
                           description (str, optional), is_public (bool, optional, default=false).
    """
    user, error_response = _get_current_user()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    if not request.is_json:
        logger.warning(f"Create template request from '{user.username}' did not contain JSON.")
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json()

    # Delegate creation logic to the controller
    template_data, error, status_code = ReportTemplateController.create_template(data, user)

    if error:
        # Controller already logged the specific error
        return jsonify({"error": error}), status_code
    # Return the created template data
    return jsonify(template_data), status_code

@report_template_bp.route('/', methods=['GET'])
@jwt_required()
# Optional: Add role/permission check decorator if needed. Usually all authenticated users can list their templates.
def list_report_templates():
    """
    API endpoint to list report templates accessible to the current user.
    Lists templates associated with forms owned by the user and any public templates.
    Requires JWT authentication.
    """
    user, error_response = _get_current_user()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Delegate listing logic to the controller
    template_list, error, status_code = ReportTemplateController.list_templates(user)

    if error:
        # Controller already logged the specific error
        return jsonify({"error": error}), status_code
    # Return the list of templates (using basic representation)
    return jsonify(template_list), status_code

@report_template_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
def get_templates_by_form(form_id):
    """
    API endpoint to retrieve templates associated with a specific form.
    Requires JWT authentication.
    User must have access to the form to see its templates.
    """
    user, error_response = _get_current_user()
    if error_response:
        return jsonify(error_response[0]), error_response[1]
    
    # Call a controller method to find templates for this form
    template_list, error, status_code = ReportTemplateController.get_templates_by_form(form_id, user)
    
    if error:
        return jsonify({"error": error}), status_code
    
    return jsonify(template_list), status_code

@report_template_bp.route('/<int:template_id>', methods=['GET'])
@jwt_required()
# Optional: Add role/permission check decorator. Access logic is handled in the controller.
def get_report_template(template_id):
    """
    API endpoint to retrieve a specific report template by its ID.
    Requires JWT authentication.
    User must own the form associated with the template, the template must be public, or user must be admin.
    """
    user, error_response = _get_current_user()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Delegate retrieval and permission check logic to the controller
    template_data, error, status_code = ReportTemplateController.get_template(template_id, user)

    if error:
        # Controller already logged the specific error
        return jsonify({"error": error}), status_code
    # Return the full template data
    return jsonify(template_data), status_code

@report_template_bp.route('/<int:template_id>', methods=['PUT'])
@jwt_required()
# Optional: Add role/permission check decorator. Access logic is handled in the controller.
def update_report_template(template_id):
    """
    API endpoint to update a specific report template.
    Requires JWT authentication. User must own the form or be an admin.
    Expects JSON body with fields to update (name, description, configuration, is_public, form_id).
    """
    user, error_response = _get_current_user()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    if not request.is_json:
        logger.warning(f"Update template request from '{user.username}' did not contain JSON.")
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json()

    # Delegate update and permission check logic to the controller
    template_data, error, status_code = ReportTemplateController.update_template(template_id, data, user)

    if error:
        # Controller already logged the specific error
        return jsonify({"error": error}), status_code
    # Return the updated template data
    return jsonify(template_data), status_code

@report_template_bp.route('/<int:template_id>', methods=['DELETE'])
@jwt_required()
# Optional: Add role/permission check decorator. Access logic is handled in the controller.
def delete_report_template(template_id):
    """
    API endpoint to soft-delete a specific report template.
    Requires JWT authentication. User must own the form or be an admin.
    """
    user, error_response = _get_current_user()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Delegate deletion and permission check logic to the controller
    error, status_code = ReportTemplateController.delete_template(template_id, user)

    if error:
        # Controller already logged the specific error
        return jsonify({"error": error}), status_code
    # Return empty response with 204 status code on successful delete
    return '', status_code