# app/views/report_views.py

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.report_controller import ReportController
from app.services.auth_service import AuthService
# Ensure necessary imports from permission_manager are present
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Create a Blueprint for report-related endpoints
report_bp = Blueprint('reports', __name__)

# --- Configuration for Report Access ---
# Define allowed roles (Adjust as needed)
REPORT_ALLOWED_ROLES = [RoleType.ADMIN, RoleType.SITE_MANAGER, RoleType.SUPERVISOR]

@report_bp.route('/generate', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(*REPORT_ALLOWED_ROLES) # Using role-based for this example
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

        # --- MODIFIED VALIDATION ---
        # Only 'report_type' is strictly required at this stage.
        # The service layer will handle logic based on whether 'columns', etc., are present.
        if not report_params.get("report_type"):
             logger.warning(f"Report generation request from {user.username} missing report_type.")
             return jsonify({"error": "Missing required report parameter: report_type"}), 400
        # --- END MODIFIED VALIDATION ---

        logger.debug(f"Received report request from {user.username}: {report_params}")

        # --- Call Controller ---
        # Delegate the core report generation logic to the controller
        # The service will now correctly handle simple vs detailed requests
        buffer, filename, mime_type, error = ReportController.generate_custom_report(report_params, user)

        # --- Handle Response ---
        if error:
            # Log the specific error
            logger.error(f"Report generation failed for user {user.username}: {error}")
            # Determine appropriate status code based on error type
            status_code = 400 # Default to Bad Request for parameter/type errors
            if "permission denied" in error.lower():
                 status_code = 403 # Forbidden
            elif "not found" in error.lower():
                 status_code = 404 # Not Found
            elif "internal" in error.lower() or "unexpected" in error.lower():
                 status_code = 500 # Internal Server Error

            return jsonify({"error": error}), status_code

        # Check if buffer or filename is missing (shouldn't happen if no error)
        if not buffer or not filename or not mime_type:
             logger.error(f"Report generation returned incomplete data despite no error for user {user.username}.")
             return jsonify({"error": "Report generation failed unexpectedly."}), 500

        # --- Send File ---
        # Return the generated file as an attachment
        logger.info(f"Successfully generated report '{filename}' for user {user.username}.")
        return send_file(
            buffer,
            mimetype=mime_type, # Use the MIME type returned by the service
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        # Catch any unexpected exceptions during view processing
        logger.exception(f"Unhandled exception in generate_report_endpoint for user {current_user_identity}: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500