# app/views/export_submission_views.py

from flask import Blueprint, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.export_submission_controller import ExportSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

export_submission_bp = Blueprint('export_submissions', __name__)

@export_submission_bp.route('/<int:submission_id>/pdf', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_submission_to_pdf(submission_id):
    """Export a form submission as PDF"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Call the controller
        pdf_data, metadata, error = ExportSubmissionController.export_submission_to_pdf(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name
        )
        
        if error:
            return jsonify({"error": error}), 400
        
        # Return the PDF file
        return send_file(
            BytesIO(pdf_data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=metadata["filename"]
        )
        
    except Exception as e:
        logger.error(f"Error exporting submission {submission_id} to PDF: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500