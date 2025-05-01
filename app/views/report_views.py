# app/views/report_views.py

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.report_controller import ReportController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Create a Blueprint for report-related endpoints
report_bp = Blueprint('reports', __name__)

# --- Configuration for Report Access ---
# Define allowed roles
REPORT_ALLOWED_ROLES = [RoleType.ADMIN, RoleType.SITE_MANAGER, RoleType.SUPERVISOR]
# Only admins can access schema information
SCHEMA_ALLOWED_ROLES = [RoleType.ADMIN]

@report_bp.route('/generate', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(*REPORT_ALLOWED_ROLES)
def generate_report_endpoint():
    """
    API endpoint to generate customizable reports.
    Expects a JSON body defining the report parameters.
    Handles both detailed requests (with columns, filters, sort)
    and simple requests (only report_type, using defaults).
    Also handles report_type="all" for multi-sheet XLSX.
    """
    try:
        # --- Authentication & User Retrieval ---
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user:
            logger.warning("Attempted report generation with invalid user identity.")
            return jsonify({"error": "User not found or invalid token"}), 404

        # --- Request Parsing & Validation ---
        report_params = request.get_json()
        if not report_params:
            logger.warning(f"Report generation request from {user.username} missing JSON body.")
            return jsonify({"error": "Request body must contain report parameters"}), 400

        # Only 'report_type' is strictly required at this stage.
        # The service layer will handle logic based on whether 'columns', etc., are present.
        if not report_params.get("report_type"):
             logger.warning(f"Report generation request from {user.username} missing report_type.")
             return jsonify({"error": "Missing required report parameter: report_type"}), 400

        logger.debug(f"Received report request from {user.username}: {report_params}")

        # --- Call Controller ---
        # Delegate the core report generation logic to the controller
        buffer, filename, mime_type, error = ReportController.generate_custom_report(report_params, user)

        # --- Handle Response ---
        if error:
            # Log the specific error
            logger.error(f"Report generation failed for user {user.username}: {error}")
            # Determine appropriate status code based on error type
            status_code = 400  # Default to Bad Request for parameter/type errors
            if "permission denied" in error.lower():
                 status_code = 403  # Forbidden
            elif "not found" in error.lower():
                 status_code = 404  # Not Found
            elif "internal" in error.lower() or "unexpected" in error.lower():
                 status_code = 500  # Internal Server Error

            return jsonify({"error": error}), status_code

        # Check if buffer or filename is missing (shouldn't happen if no error)
        if not buffer or not filename or not mime_type:
             logger.error(f"Report generation returned incomplete data despite no error for user {user.username}.")
             return jsonify({"error": "Report generation failed unexpectedly."}), 500

        # --- Send File ---
        # Return the generated file as an attachment
        logger.info(f"Successfully generated report '{filename}' for user {user.username}.")
        return send_file(
            BytesIO(buffer.getvalue()),  # Ensure we're sending a new BytesIO object
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        # Catch any unexpected exceptions during view processing
        logger.exception(f"Unhandled exception in generate_report_endpoint for user {get_jwt_identity()}: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


@report_bp.route('/schema', methods=['GET'])
@jwt_required()
@PermissionManager.require_role(*SCHEMA_ALLOWED_ROLES)
def get_database_schema_endpoint():
    """
    API endpoint to retrieve database schema and table row counts.
    Returns information about all tables, their columns, and the current row count.
    Only accessible to administrators.
    """
    try:
        # --- Authentication & User Retrieval ---
        current_user_identity = get_jwt_identity()
        user = AuthService.get_current_user(current_user_identity)
        if not user:
            logger.warning("Attempted schema retrieval with invalid user identity.")
            return jsonify({"error": "User not found or invalid token"}), 404

        logger.info(f"Database schema request received from user {user.username}")

        # Call the controller to get schema data
        schema_data, error = ReportController.get_database_schema(user)
        
        if error:
            logger.error(f"Schema retrieval failed for user {user.username}: {error}")
            return jsonify({"error": error}), 500
            
        logger.info(f"Successfully retrieved schema information for user {user.username}")
        return jsonify(schema_data), 200
            
    except Exception as e:
        logger.exception(f"Unhandled exception in get_database_schema_endpoint for user {get_jwt_identity()}: {e}")
        return jsonify({"error": "An internal server error occurred while retrieving database schema."}), 500