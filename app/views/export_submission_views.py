# app/views/export_submission_views.py

from flask import Blueprint, request, send_file, jsonify, current_app
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
    
@export_submission_bp.route('/<int:submission_id>/pdf/logo', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_submission_to_pdf_with_logo(submission_id):
    """
    Export a form submission as PDF with optional header image
    
    Request form parameters:
    - header_image: Image file (PNG, JPEG) to use as header
    - header_opacity: Opacity value (0-100) for the header image
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get header image and opacity from request
        header_image = None
        header_opacity = 1.0  # Default opacity
        
        if 'header_image' in request.files:
            header_image = request.files['header_image']
            
            # Validate file type
            if not header_image.filename or not header_image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                return jsonify({"error": "Header image must be PNG or JPEG format"}), 400
        
        # Get opacity from form data (0-100 scale)
        if 'header_opacity' in request.form:
            try:
                # Convert from percentage (0-100) to decimal (0.0-1.0)
                opacity_value = float(request.form['header_opacity'])
                header_opacity = max(0.0, min(100.0, opacity_value)) / 100.0
            except ValueError:
                return jsonify({"error": "Header opacity must be a number between 0 and 100"}), 400
        
        # Call the controller
        pdf_data, metadata, error = ExportSubmissionController.export_submission_to_pdf_with_logo(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name,
            header_image=header_image,
            header_opacity=header_opacity
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