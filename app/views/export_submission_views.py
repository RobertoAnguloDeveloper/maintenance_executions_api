# app/views/export_submission_views.py

from flask import Blueprint, request, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.export_submission_controller import ExportSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType
from app.services.export_submission_service import DEFAULT_STYLE_CONFIG # Import for keys
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

export_submission_bp = Blueprint('export_submissions', __name__)

# Helper to extract PDF/DOCX style options from request form/args
def _extract_style_options(source_data): # Can be request.form or request.args
    style_options = {}
    # Use keys from DEFAULT_STYLE_CONFIG as a base for known style parameters
    # This helps in collecting relevant fields, though DOCX interpretation will differ.
    for key in DEFAULT_STYLE_CONFIG.keys(): # Using PDF config as a proxy for potential style keys
        if key in source_data and source_data[key]:
            style_options[key] = source_data[key]
    # Add any DOCX-specific style keys if needed, e.g.:
    # if 'docx_font_color' in source_data: style_options['docx_font_color'] = source_data['docx_font_color']
    return style_options

@export_submission_bp.route('/<int:submission_id>/pdf', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_submission_to_pdf(submission_id):
    """Export a form submission as PDF (basic GET version)"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        pdf_style_options = _extract_style_options(request.args) # For GET, options from query params

        pdf_data, metadata, error = ExportSubmissionController.export_submission_to_pdf(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name,
            pdf_style_options=pdf_style_options
        )

        if error:
            return jsonify({"error": error}), 400

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
    Export a form submission as PDF with optional header image and full style customization.
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        header_image = None
        header_opacity = 1.0
        header_size = None
        header_width = None
        header_height = None
        header_alignment = "center"
        signatures_size = 100
        signatures_alignment = "vertical"
        structured = True # Default from original code

        if 'header_image' in request.files:
            header_image = request.files['header_image']
            if not header_image.filename or not header_image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
                return jsonify({"error": "Header image must be PNG, JPEG, or SVG format"}), 400

        if 'header_opacity' in request.form and request.form['header_opacity']:
            try:
                opacity_value = float(request.form['header_opacity'])
                header_opacity = max(0.0, min(100.0, opacity_value)) / 100.0
            except ValueError:
                return jsonify({"error": "Header opacity must be a number between 0 and 100"}), 400

        if 'header_size' in request.form and request.form['header_size']:
            try:
                header_size = float(request.form['header_size'])
                if header_size <= 0:
                    return jsonify({"error": "Header size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Header size must be a number"}), 400

        if 'header_width' in request.form and request.form['header_width']:
            try:
                header_width = float(request.form['header_width'])
                if header_width <= 0:
                    return jsonify({"error": "Header width must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header width must be a number"}), 400

        if 'header_height' in request.form and request.form['header_height']:
            try:
                header_height = float(request.form['header_height'])
                if header_height <= 0:
                    return jsonify({"error": "Header height must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header height must be a number"}), 400

        if 'header_alignment' in request.form and request.form['header_alignment']:
            alignment = request.form['header_alignment'].lower()
            valid_alignments = ['left', 'center', 'right']
            if alignment not in valid_alignments:
                return jsonify({"error": f"Invalid header alignment. Must be one of: {', '.join(valid_alignments)}"}), 400
            header_alignment = alignment

        if 'signatures_size' in request.form and request.form['signatures_size']:
            try:
                signatures_size = float(request.form['signatures_size'])
                if signatures_size <= 0:
                    return jsonify({"error": "Signatures size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Signatures size must be a number"}), 400

        if 'signatures_alignment' in request.form and request.form['signatures_alignment']:
            sig_alignment = request.form['signatures_alignment'].lower()
            valid_sig_alignments = ['vertical', 'horizontal']
            if sig_alignment not in valid_sig_alignments:
                return jsonify({"error": f"Invalid signatures alignment. Must be one of: {', '.join(valid_sig_alignments)}"}), 400
            signatures_alignment = sig_alignment

        if 'structured' in request.form:
            structured_value = request.form['structured'].lower()
            structured = structured_value in ['true', 'yes', '1', 'on']

        pdf_style_options = _extract_style_options(request.form)
        logger.debug(f"Exporting PDF with logo: submission_id={submission_id}, header_size={header_size}, structured={structured}, pdf_style_options_count={len(pdf_style_options)}")

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
            signatures_alignment=signatures_alignment,
            structured=structured,
            pdf_style_options=pdf_style_options
        )

        if error:
            return jsonify({"error": error}), 400

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
    Export a form submission as PDF with structured organization and full style customization.
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        header_image = None
        header_opacity = 1.0
        header_size = None
        header_width = None
        header_height = None
        header_alignment = "center"
        signatures_size = 100
        signatures_alignment = "vertical"

        if 'header_image' in request.files:
            header_image = request.files['header_image']
            if not header_image.filename or not header_image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
                return jsonify({"error": "Header image must be PNG, JPEG, or SVG format"}), 400

        if 'header_opacity' in request.form and request.form['header_opacity']:
            try:
                opacity_value = float(request.form['header_opacity'])
                header_opacity = max(0.0, min(100.0, opacity_value)) / 100.0
            except ValueError:
                return jsonify({"error": "Header opacity must be a number between 0 and 100"}), 400

        if 'header_size' in request.form and request.form['header_size']:
            try:
                header_size = float(request.form['header_size'])
                if header_size <= 0:
                    return jsonify({"error": "Header size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Header size must be a number"}), 400

        if 'header_width' in request.form and request.form['header_width']:
            try:
                header_width = float(request.form['header_width'])
                if header_width <= 0:
                    return jsonify({"error": "Header width must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header width must be a number"}), 400

        if 'header_height' in request.form and request.form['header_height']:
            try:
                header_height = float(request.form['header_height'])
                if header_height <= 0:
                    return jsonify({"error": "Header height must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header height must be a number"}), 400

        if 'header_alignment' in request.form and request.form['header_alignment']:
            alignment = request.form['header_alignment'].lower()
            valid_alignments = ['left', 'center', 'right']
            if alignment not in valid_alignments:
                return jsonify({"error": f"Invalid header alignment. Must be one of: {', '.join(valid_alignments)}"}), 400
            header_alignment = alignment

        if 'signatures_size' in request.form and request.form['signatures_size']:
            try:
                signatures_size = float(request.form['signatures_size'])
                if signatures_size <= 0:
                    return jsonify({"error": "Signatures size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Signatures size must be a number"}), 400

        if 'signatures_alignment' in request.form and request.form['signatures_alignment']:
            sig_alignment = request.form['signatures_alignment'].lower()
            valid_sig_alignments = ['vertical', 'horizontal']
            if sig_alignment not in valid_sig_alignments:
                return jsonify({"error": f"Invalid signatures alignment. Must be one of: {', '.join(valid_sig_alignments)}"}), 400
            signatures_alignment = sig_alignment

        pdf_style_options = _extract_style_options(request.form)
        logger.debug(f"Exporting structured PDF: submission_id={submission_id}, pdf_style_options_count={len(pdf_style_options)}")

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
            signatures_alignment=signatures_alignment,
            pdf_style_options=pdf_style_options
        )

        if error:
            return jsonify({"error": error}), 400

        return send_file(
            BytesIO(pdf_data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=metadata["filename"]
        )

    except Exception as e:
        logger.error(f"Error exporting structured submission {submission_id} to PDF: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# --- NEW DOCX EXPORT ROUTE ---
@export_submission_bp.route('/<int:submission_id>/docx', methods=['POST']) # Changed to POST to accept form data for styling
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS) # Assuming 'view' permission is sufficient
def export_submission_to_docx(submission_id):
    """
    Export a form submission as DOCX with optional header image and style customization.
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Extract common parameters (similar to PDF export)
        header_image = None
        header_size = None # Percentage
        header_width = None # Pixels
        header_height = None # Pixels
        header_alignment = "center"
        signatures_size = 100 # Percentage
        signatures_alignment = "vertical"

        if 'header_image' in request.files:
            header_image = request.files['header_image']
            # Basic validation, specific format needs for DOCX might differ or require conversion
            if not header_image.filename or not header_image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                 # SVG might need server-side conversion for python-docx, stick to common raster for now
                return jsonify({"error": "Header image for DOCX should be PNG, JPEG."}), 400

        if 'header_size' in request.form and request.form['header_size']:
            try:
                header_size = float(request.form['header_size'])
                if header_size <= 0:
                    return jsonify({"error": "Header size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Header size must be a number"}), 400

        if 'header_width' in request.form and request.form['header_width']:
            try:
                header_width = float(request.form['header_width'])
                if header_width <= 0:
                    return jsonify({"error": "Header width must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header width must be a number"}), 400

        if 'header_height' in request.form and request.form['header_height']:
            try:
                header_height = float(request.form['header_height'])
                if header_height <= 0:
                    return jsonify({"error": "Header height must be positive"}), 400
            except ValueError:
                return jsonify({"error": "Header height must be a number"}), 400

        if 'header_alignment' in request.form and request.form['header_alignment']:
            alignment = request.form['header_alignment'].lower()
            valid_alignments = ['left', 'center', 'right'] # DOCX alignments
            if alignment not in valid_alignments:
                return jsonify({"error": f"Invalid header alignment. Must be one of: {', '.join(valid_alignments)}"}), 400
            header_alignment = alignment

        if 'signatures_size' in request.form and request.form['signatures_size']:
            try:
                signatures_size = float(request.form['signatures_size'])
                if signatures_size <= 0:
                    return jsonify({"error": "Signatures size must be greater than 0 percent"}), 400
            except ValueError:
                return jsonify({"error": "Signatures size must be a number"}), 400

        if 'signatures_alignment' in request.form and request.form['signatures_alignment']:
            sig_alignment = request.form['signatures_alignment'].lower()
            valid_sig_alignments = ['vertical', 'horizontal'] # For DOCX layout
            if sig_alignment not in valid_sig_alignments:
                return jsonify({"error": f"Invalid signatures alignment. Must be one of: {', '.join(valid_sig_alignments)}"}), 400
            signatures_alignment = sig_alignment

        # Extract generic style options (can be a subset of PDF's or DOCX specific)
        style_options = _extract_style_options(request.form)
        logger.debug(f"Exporting DOCX: submission_id={submission_id}, style_options_count={len(style_options)}")

        docx_data, metadata, error = ExportSubmissionController.export_submission_to_docx(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name,
            header_image=header_image,
            header_size=header_size,
            header_width=header_width,
            header_height=header_height,
            header_alignment=header_alignment,
            signatures_size=signatures_size,
            signatures_alignment=signatures_alignment,
            style_options=style_options
        )

        if error:
            return jsonify({"error": error}), 400

        return send_file(
            BytesIO(docx_data),
            mimetype=metadata["mimetype"], # "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            as_attachment=True,
            download_name=metadata["filename"]
        )

    except Exception as e:
        logger.error(f"Error exporting submission {submission_id} to DOCX: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
