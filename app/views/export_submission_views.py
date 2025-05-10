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
    - header_size: Size percentage (1-500) for the header image
      Note: Use 100 for original size, values below 100 reduce size, above 100 increase size
    - header_width: Width in pixels (overrides header_size if both provided)
    - header_height: Height in pixels (overrides header_size if both provided)
    - header_alignment: Alignment of the header image (left, center, right)
    - signatures_size: Size percentage for signature images (100 = original size)
    - signatures_alignment: Layout for signatures (vertical, horizontal)
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get header image and opacity from request
        header_image = None
        header_opacity = 1.0  # Default opacity
        header_size = None
        header_width = None
        header_height = None
        header_alignment = "center"  # Default alignment
        signatures_size = 100  # Default signature size (100%)
        signatures_alignment = "vertical"  # Default signature alignment
        
        if 'header_image' in request.files:
            header_image = request.files['header_image']
            
            # Validate file type
            if not header_image.filename or not header_image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                return jsonify({"error": "Header image must be PNG or JPEG format"}), 400
        
        # Get opacity from form data (0-100 scale)
        if 'header_opacity' in request.form and request.form['header_opacity']:
            try:
                # Convert from percentage (0-100) to decimal (0.0-1.0)
                opacity_value = float(request.form['header_opacity'])
                header_opacity = max(0.0, min(100.0, opacity_value)) / 100.0
            except ValueError:
                return jsonify({"error": "Header opacity must be a number between 0 and 100"}), 400
        
        # Get size percentage (keeps aspect ratio)
        if 'header_size' in request.form and request.form['header_size']:
            try:
                header_size = float(request.form['header_size'])
                # Allow values from 1 to 500%
                if header_size <= 0:
                    return jsonify({"error": "Header size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Header size must be a number"}), 400
        
        # Get width (in pixels)
        if 'header_width' in request.form and request.form['header_width']:
            try:
                header_width = float(request.form['header_width'])
                if header_width <= 0:
                    return jsonify({"error": "Header width must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header width must be a number"}), 400
        
        # Get height (in pixels)
        if 'header_height' in request.form and request.form['header_height']:
            try:
                header_height = float(request.form['header_height'])
                if header_height <= 0:
                    return jsonify({"error": "Header height must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header height must be a number"}), 400
        
        # Get header alignment
        if 'header_alignment' in request.form and request.form['header_alignment']:
            alignment = request.form['header_alignment'].lower()
            valid_alignments = ['left', 'center', 'right']
            if alignment not in valid_alignments:
                return jsonify({"error": f"Invalid header alignment. Must be one of: {', '.join(valid_alignments)}"}), 400
            header_alignment = alignment
            
        # Get signatures size
        if 'signatures_size' in request.form and request.form['signatures_size']:
            try:
                signatures_size = float(request.form['signatures_size'])
                if signatures_size <= 0:
                    return jsonify({"error": "Signatures size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Signatures size must be a number"}), 400
                
        # Get signatures alignment
        if 'signatures_alignment' in request.form and request.form['signatures_alignment']:
            sig_alignment = request.form['signatures_alignment'].lower()
            valid_sig_alignments = ['vertical', 'horizontal']
            if sig_alignment not in valid_sig_alignments:
                return jsonify({"error": f"Invalid signatures alignment. Must be one of: {', '.join(valid_sig_alignments)}"}), 400
            signatures_alignment = sig_alignment
        
        # Call the controller
        pdf_data, metadata, error = ExportSubmissionController.export_submission_to_pdf_with_logo(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name,
            header_image=header_image,
            header_opacity=header_opacity,
            header_size=header_size,
            header_width=header_width,
            header_height=header_height,
            header_alignment=header_alignment,
            signatures_size=signatures_size,
            signatures_alignment=signatures_alignment
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
        logger.error(f"Error exporting submission {submission_id} to PDF with logo: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@export_submission_bp.route('/<int:submission_id>/pdf/structured', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_structured_submission_to_pdf(submission_id):
    """
    Export a form submission as PDF with structured organization of tables and dropdowns
    
    Request form parameters:
    - header_image: Image file (PNG, JPEG) to use as header
    - header_opacity: Opacity value (0-100) for the header image
    - header_size: Size percentage (1-500) for the header image
      Note: Use 100 for original size, values below 100 reduce size, above 100 increase size
    - header_width: Width in pixels (overrides header_size if both provided)
    - header_height: Height in pixels (overrides header_size if both provided)
    - header_alignment: Alignment of the header image (left, center, right)
    - signatures_size: Size percentage for signature images (100 = original size)
    - signatures_alignment: Layout for signatures (vertical, horizontal)
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get header image and opacity from request (same parameters as pdf/logo endpoint)
        header_image = None
        header_opacity = 1.0  # Default opacity
        header_size = None
        header_width = None
        header_height = None
        header_alignment = "center"  # Default alignment
        signatures_size = 100  # Default signature size (100%)
        signatures_alignment = "vertical"  # Default signature alignment
        
        if 'header_image' in request.files:
            header_image = request.files['header_image']
            
            # Validate file type
            if not header_image.filename or not header_image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                return jsonify({"error": "Header image must be PNG or JPEG format"}), 400
        
        # Get opacity from form data (0-100 scale)
        if 'header_opacity' in request.form and request.form['header_opacity']:
            try:
                # Convert from percentage (0-100) to decimal (0.0-1.0)
                opacity_value = float(request.form['header_opacity'])
                header_opacity = max(0.0, min(100.0, opacity_value)) / 100.0
            except ValueError:
                return jsonify({"error": "Header opacity must be a number between 0 and 100"}), 400
        
        # Get size percentage (keeps aspect ratio)
        if 'header_size' in request.form and request.form['header_size']:
            try:
                header_size = float(request.form['header_size'])
                # Allow values from 1 to 500%
                if header_size <= 0:
                    return jsonify({"error": "Header size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Header size must be a number"}), 400
        
        # Get width (in pixels)
        if 'header_width' in request.form and request.form['header_width']:
            try:
                header_width = float(request.form['header_width'])
                if header_width <= 0:
                    return jsonify({"error": "Header width must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header width must be a number"}), 400
        
        # Get height (in pixels)
        if 'header_height' in request.form and request.form['header_height']:
            try:
                header_height = float(request.form['header_height'])
                if header_height <= 0:
                    return jsonify({"error": "Header height must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header height must be a number"}), 400
        
        # Get header alignment
        if 'header_alignment' in request.form and request.form['header_alignment']:
            alignment = request.form['header_alignment'].lower()
            valid_alignments = ['left', 'center', 'right']
            if alignment not in valid_alignments:
                return jsonify({"error": f"Invalid header alignment. Must be one of: {', '.join(valid_alignments)}"}), 400
            header_alignment = alignment
            
        # Get signatures size
        if 'signatures_size' in request.form and request.form['signatures_size']:
            try:
                signatures_size = float(request.form['signatures_size'])
                if signatures_size <= 0:
                    return jsonify({"error": "Signatures size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Signatures size must be a number"}), 400
                
        # Get signatures alignment
        if 'signatures_alignment' in request.form and request.form['signatures_alignment']:
            sig_alignment = request.form['signatures_alignment'].lower()
            valid_sig_alignments = ['vertical', 'horizontal']
            if sig_alignment not in valid_sig_alignments:
                return jsonify({"error": f"Invalid signatures alignment. Must be one of: {', '.join(valid_sig_alignments)}"}), 400
            signatures_alignment = sig_alignment
        
        # Call the controller
        pdf_data, metadata, error = ExportSubmissionController.export_structured_submission_to_pdf(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name,
            header_image=header_image,
            header_opacity=header_opacity,
            header_size=header_size,
            header_width=header_width,
            header_height=header_height,
            header_alignment=header_alignment,
            signatures_size=signatures_size,
            signatures_alignment=signatures_alignment
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
        logger.error(f"Error exporting structured submission {submission_id} to PDF: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500