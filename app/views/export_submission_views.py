# app/views/export_submission_views.py

from flask import Blueprint, request, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.export_submission_controller import ExportSubmissionController
from app.services.auth_service import AuthService # Assuming AuthService.get_current_user exists and works
from app.utils.permission_manager import PermissionManager, EntityType # Assuming these are correctly set up
from app.services.export_submission_service import DEFAULT_STYLE_CONFIG # Import for keys
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

export_submission_bp = Blueprint('export_submissions', __name__, url_prefix='/api/export_submissions')

def _extract_style_options(source_data): # source_data is request.form
    style_options = {}
    # Using PDF config as a proxy for potential style keys for both PDF and DOCX styling.
    # The service layer is responsible for interpreting these for the specific format.
    for key in DEFAULT_STYLE_CONFIG.keys(): 
        if key in source_data and source_data[key] is not None and source_data[key] != '':
            style_options[key] = source_data[key]
    # Add any other specific keys you might want to always check for
    # e.g., if 'custom_docx_setting' in source_data: style_options['custom_docx_setting'] = source_data['custom_docx_setting']
    return style_options

def _parse_common_export_params(current_request): # Changed parameter name for clarity
    """Helper to parse common parameters for custom exports from the Flask request object."""
    params = {}
    # Access files from current_request.files
    params['header_image'] = current_request.files.get('header_image')
    
    if params['header_image']:
        # Basic validation, specific format needs for DOCX might differ or require conversion
        if not params['header_image'].filename or not params['header_image'].filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')): # SVG for PDF, not ideal for DOCX directly
            raise ValueError("Header image must be PNG, JPEG, or SVG format.")

    # Access form data from current_request.form
    form_data = current_request.form

    if 'header_opacity' in form_data and form_data['header_opacity']:
        try:
            opacity_value = float(form_data['header_opacity'])
            params['header_opacity'] = max(0.0, min(100.0, opacity_value)) / 100.0 # For PDF
        except ValueError:
            raise ValueError("Header opacity must be a number between 0 and 100.")

    if 'header_size' in form_data and form_data['header_size']:
        try:
            params['header_size'] = float(form_data['header_size'])
            if params['header_size'] <= 0:
                raise ValueError("Header size must be greater than 0 percent.")
        except ValueError:
            raise ValueError("Header size must be a number.")
    
    if 'header_width' in form_data and form_data['header_width']:
        try:
            params['header_width'] = float(form_data['header_width'])
            if params['header_width'] <= 0:
                raise ValueError("Header width must be positive.")
        except ValueError:
            raise ValueError("Header width must be a number.")

    if 'header_height' in form_data and form_data['header_height']:
        try:
            params['header_height'] = float(form_data['header_height'])
            if params['header_height'] <= 0:
                raise ValueError("Header height must be positive.")
        except ValueError:
            raise ValueError("Header height must be a number.")

    if 'header_alignment' in form_data and form_data['header_alignment']:
        alignment = form_data['header_alignment'].lower()
        valid_alignments = ['left', 'center', 'right']
        if alignment not in valid_alignments:
            raise ValueError(f"Invalid header alignment. Must be one of: {', '.join(valid_alignments)}.")
        params['header_alignment'] = alignment

    if 'signatures_size' in form_data and form_data['signatures_size']:
        try:
            params['signatures_size'] = float(form_data['signatures_size'])
            if params['signatures_size'] <= 0:
                raise ValueError("Signatures size must be greater than 0 percent.")
        except ValueError:
            raise ValueError("Signatures size must be a number.")
            
    if 'signatures_alignment' in form_data and form_data['signatures_alignment']:
        sig_alignment = form_data['signatures_alignment'].lower()
        valid_sig_alignments = ['vertical', 'horizontal']
        if sig_alignment not in valid_sig_alignments:
            raise ValueError(f"Invalid signatures alignment. Must be one of: {', '.join(valid_sig_alignments)}.")
        params['signatures_alignment'] = sig_alignment
        
    if 'include_signatures' in form_data: # Allow explicit control over including signatures
        params['include_signatures'] = form_data['include_signatures'].lower() in ['true', '1', 'yes', 'on']

    return params

# --- NEW Endpoint for Customization Options ---
@export_submission_bp.route('/customization_options', methods=['GET'])
def get_export_customization_options():
    """
    Provides a list of all accepted parameters for custom PDF and DOCX export requests,
    including their descriptions, types, and example values.
    """
    options = {
        "common_options": [
            {
                "key": "header_image", 
                "type": "file", 
                "description": "Image file to be placed at the top of the document.",
                "notes": "Supported formats: PNG, JPG, JPEG, SVG (SVG primarily for PDF, may require conversion for DOCX by the service)."
            },
            {
                "key": "header_opacity", 
                "type": "float", 
                "description": "Opacity of the header image (0-100). Only applicable for PDF.",
                "example_pdf": "80",
                "notes": "Service converts to a 0.0-1.0 scale for PDF."
            },
            {
                "key": "header_size", 
                "type": "float", 
                "description": "Relative size of the header image as a percentage of its original dimensions (e.g., 50 for 50%).",
                "example_pdf": "50", 
                "example_docx": "50"
            },
            {
                "key": "header_width", 
                "type": "float", 
                "description": "Specific width for the header image in pixels. Overrides header_size if both width and height are set.",
                "example_pdf": "200", 
                "example_docx": "200"
            },
            {
                "key": "header_height", 
                "type": "float", 
                "description": "Specific height for the header image in pixels. Overrides header_size if both width and height are set.",
                "example_pdf": "100", 
                "example_docx": "100"
            },
            {
                "key": "header_alignment", 
                "type": "string", 
                "description": "Alignment of the header image.",
                "accepted_values": ["left", "center", "right"],
                "example_pdf": "center", 
                "example_docx": "center"
            },
            {
                "key": "signatures_size", 
                "type": "float", 
                "description": "Relative size of signature images as a percentage (e.g., 80 for 80% of configured default).",
                "example_pdf": "80", 
                "example_docx": "80"
            },
            {
                "key": "signatures_alignment", 
                "type": "string", 
                "description": "Layout alignment for multiple signatures.",
                "accepted_values": ["vertical", "horizontal"],
                "example_pdf": "vertical", 
                "example_docx": "vertical"
            },
            {
                "key": "include_signatures", 
                "type": "boolean", 
                "description": "Whether to include signatures in the export.",
                "accepted_values": ["true", "1", "yes", "on", "false", "0", "no", "off"],
                "example_pdf": "true", 
                "example_docx": "true"
            }
        ],
        "style_options": [] # To be populated from DEFAULT_STYLE_CONFIG
    }

    # Populate style_options from DEFAULT_STYLE_CONFIG
    # These keys are primarily based on PDF (ReportLab) needs but are adapted by the DOCX service.
    for key, default_value in DEFAULT_STYLE_CONFIG.items():
        param_info = {"key": key, "description": f"Styling for {key.replace('_', ' ')}."}
        
        if key.endswith("_color"):
            param_info["type"] = "string (color)"
            param_info["example_pdf"] = "#RRGGBB or color name (e.g., 'red', 'black')"
            param_info["example_docx"] = "#RRGGBB or color name (e.g., 'red', 'black')"
            param_info["notes"] = "Service attempts to map common names and hex codes."
        elif key.endswith("_font_family"):
            param_info["type"] = "string (font name)"
            param_info["example_pdf"] = "Helvetica-Bold"
            param_info["example_docx"] = "Arial" # DOCX uses standard font names
            param_info["notes"] = "Ensure font is available. PDF uses PostScript names, DOCX uses system font names."
        elif key.endswith("_font_size") or "_leading" in key or key.endswith("_padding") or "_indent" in key or key.endswith("_thickness") or key.endswith("_same_line_max_length"):
            param_info["type"] = "float or integer"
            param_info["example_pdf"] = "12" # Typically points
            param_info["example_docx"] = "12" # Typically points
            param_info["notes"] = "Units are generally points. Service converts for DOCX where necessary (e.g., to Pt() or Inches())."
        elif key.endswith("_alignment"):
            param_info["type"] = "string or integer"
            param_info["accepted_values_pdf"] = ["LEFT/0", "CENTER/1", "RIGHT/2", "JUSTIFY/4"]
            param_info["accepted_values_docx"] = ["LEFT", "CENTER", "RIGHT", "JUSTIFY"]
            param_info["example_pdf"] = "CENTER"
            param_info["example_docx"] = "CENTER"
        elif key.startswith("page_margin_") or "_space_" in key or key.startswith("signature_image_"):
            param_info["type"] = "float"
            param_info["example_pdf"] = "0.5" # Typically inches for ReportLab
            param_info["example_docx"] = "0.5" # Service converts to Inches() for DOCX
            param_info["notes"] = "Units are typically inches for PDF spacing/margins. Service converts for DOCX."
        elif key == "qa_layout":
            param_info["type"] = "string"
            param_info["accepted_values"] = ["answer_below", "answer_same_line"]
            param_info["example_pdf"] = "answer_below"
            param_info["example_docx"] = "answer_below"
        else:
            param_info["type"] = "string or float" # Generic fallback
            param_info["example_pdf"] = str(default_value) if not callable(default_value) else "varies"
            param_info["example_docx"] = str(default_value) if not callable(default_value) else "varies"

        options["style_options"].append(param_info)
        
    return jsonify(options), 200


# --- PDF Endpoints ---

@export_submission_bp.route('/<int:submission_id>/pdf', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_default_submission_to_pdf(submission_id):
    """Export a form submission as PDF with default styling."""
    try:
        current_user_identity = get_jwt_identity()
        # user = AuthService.get_current_user(current_user_identity) # Assuming you need user object for role
        # user_role = user.role.name if user and user.role else None
        user_claims = current_user_identity # If JWT sub is just the username or ID and role is in claims
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None


        pdf_data, metadata, error = ExportSubmissionController.generate_pdf_export(
            submission_id=submission_id,
            current_user=str(user_claims), # Pass identifier
            user_role=user_role
            # All other options will use their defaults in the controller/service
        )

        if error:
            return jsonify({"error": error}), 400 if error == "Submission not found" else 500

        return send_file(
            BytesIO(pdf_data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=metadata["filename"]
        )
    except Exception as e:
        logger.error(f"Error exporting default PDF for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during PDF export"}), 500

@export_submission_bp.route('/<int:submission_id>/pdf/custom', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_custom_submission_to_pdf(submission_id):
    """Export a form submission as PDF with custom styling and options."""
    try:
        current_user_identity = get_jwt_identity()
        # user = AuthService.get_current_user(current_user_identity)
        # user_role = user.role.name if user and user.role else None
        user_claims = current_user_identity 
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request) # request.form and request.files are part of request
        
        pdf_style_options = _extract_style_options(request.form)
        logger.debug(f"Custom PDF export: submission_id={submission_id}, style_options_count={len(pdf_style_options)}")

        pdf_data, metadata, error = ExportSubmissionController.generate_pdf_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role,
            header_image=common_params.get('header_image'),
            header_opacity=common_params.get('header_opacity', 1.0),
            header_size=common_params.get('header_size'),
            header_width=common_params.get('header_width'),
            header_height=common_params.get('header_height'),
            header_alignment=common_params.get('header_alignment', "center"),
            signatures_size=common_params.get('signatures_size', 100),
            signatures_alignment=common_params.get('signatures_alignment', "vertical"),
            include_signatures=common_params.get('include_signatures', True),
            pdf_style_options=pdf_style_options
        )

        if error:
            return jsonify({"error": error}), 400 if "not found" in error.lower() else 500
        
        return send_file(
            BytesIO(pdf_data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=metadata["filename"]
        )
    except ValueError as ve: # Catch specific errors from _parse_common_export_params
        logger.warning(f"Validation error during custom PDF export for submission {submission_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error exporting custom PDF for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during PDF export"}), 500

@export_submission_bp.route('/<int:submission_id>/pdf/logo', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_custom_submission_to_pdf_logo(submission_id):
    """Export a form submission as PDF with custom styling and options."""
    try:
        current_user_identity = get_jwt_identity()
        # user = AuthService.get_current_user(current_user_identity)
        # user_role = user.role.name if user and user.role else None
        user_claims = current_user_identity 
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request) # request.form and request.files are part of request
        
        pdf_style_options = _extract_style_options(request.form)
        logger.debug(f"Custom PDF export: submission_id={submission_id}, style_options_count={len(pdf_style_options)}")

        pdf_data, metadata, error = ExportSubmissionController.generate_pdf_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role,
            header_image=common_params.get('header_image'),
            header_opacity=common_params.get('header_opacity', 1.0),
            header_size=common_params.get('header_size'),
            header_width=common_params.get('header_width'),
            header_height=common_params.get('header_height'),
            header_alignment=common_params.get('header_alignment', "center"),
            signatures_size=common_params.get('signatures_size', 100),
            signatures_alignment=common_params.get('signatures_alignment', "vertical"),
            include_signatures=common_params.get('include_signatures', True),
            pdf_style_options=pdf_style_options
        )

        if error:
            return jsonify({"error": error}), 400 if "not found" in error.lower() else 500
        
        return send_file(
            BytesIO(pdf_data),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=metadata["filename"]
        )
    except ValueError as ve: # Catch specific errors from _parse_common_export_params
        logger.warning(f"Validation error during custom PDF export for submission {submission_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error exporting custom PDF for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during PDF export"}), 500

# --- DOCX Endpoints ---

@export_submission_bp.route('/<int:submission_id>/docx', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_default_submission_to_docx(submission_id):
    """Export a form submission as DOCX with default styling."""
    try:
        current_user_identity = get_jwt_identity()
        # user = AuthService.get_current_user(current_user_identity)
        # user_role = user.role.name if user and user.role else None
        user_claims = current_user_identity
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        docx_data, metadata, error = ExportSubmissionController.generate_docx_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role
            # All other options will use their defaults
        )

        if error:
            return jsonify({"error": error}), 400 if error == "Submission not found" else 500

        return send_file(
            BytesIO(docx_data),
            mimetype=metadata["mimetype"],
            as_attachment=True,
            download_name=metadata["filename"]
        )
    except Exception as e:
        logger.error(f"Error exporting default DOCX for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during DOCX export"}), 500

@export_submission_bp.route('/<int:submission_id>/docx/custom', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_custom_submission_to_docx(submission_id):
    """Export a form submission as DOCX with custom styling and options."""
    try:
        current_user_identity = get_jwt_identity()
        # user = AuthService.get_current_user(current_user_identity)
        # user_role = user.role.name if user and user.role else None
        user_claims = current_user_identity
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request) # Pass the whole request object
        
        # For DOCX, 'style_options' is the key used in the controller and service
        style_options = _extract_style_options(request.form) 
        logger.debug(f"Custom DOCX export: submission_id={submission_id}, style_options_count={len(style_options)}")

        docx_data, metadata, error = ExportSubmissionController.generate_docx_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role,
            header_image=common_params.get('header_image'),
            header_size=common_params.get('header_size'), # Percentage
            header_width=common_params.get('header_width'), # Pixels
            header_height=common_params.get('header_height'), # Pixels
            header_alignment=common_params.get('header_alignment', "center"),
            signatures_size=common_params.get('signatures_size', 100), # Percentage
            signatures_alignment=common_params.get('signatures_alignment', "vertical"),
            include_signatures=common_params.get('include_signatures', True),
            style_options=style_options
        )

        if error:
            return jsonify({"error": error}), 400 if "not found" in error.lower() else 500
        
        return send_file(
            BytesIO(docx_data),
            mimetype=metadata["mimetype"],
            as_attachment=True,
            download_name=metadata["filename"]
        )
    except ValueError as ve:
        logger.warning(f"Validation error during custom DOCX export for submission {submission_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error exporting custom DOCX for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during DOCX export"}), 500
