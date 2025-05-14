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

# --- Updated Endpoint for Customization Options ---
@export_submission_bp.route('/customization_options', methods=['GET'])
def get_export_customization_options():
    """
    Provides a list of all accepted parameters for custom PDF and DOCX export requests,
    including their descriptions, types, example values, and applicability.
    """
    options = {
        "common_options": [
            {
                "key": "header_image",
                "type": "file",
                "description": "Image file to be placed at the top of the document.",
                "notes": "Supported formats: PNG, JPG, JPEG, SVG. SVG is primarily for PDF and may be converted to PNG for DOCX by the service."
            },
            {
                "key": "header_opacity",
                "type": "float",
                "description": "Opacity of the header image (0-100).",
                "example_pdf": "80",
                "example_docx": "N/A (Opacity is typically a PDF-specific feature and may not apply to DOCX headers directly).",
                "notes": "Service converts to a 0.0-1.0 scale for PDF. For DOCX, this option is unlikely to have an effect."
            },
            {
                "key": "header_size",
                "type": "float",
                "description": "Relative size of the header image as a percentage of its original dimensions (e.g., 50 for 50%). If header_width or header_height are set, they take precedence.",
                "example_pdf": "50",
                "example_docx": "50"
            },
            {
                "key": "header_width",
                "type": "float",
                "description": "Specific width for the header image in pixels. Overrides header_size if set. Aspect ratio is maintained if only width or height is set.",
                "example_pdf": "200",
                "example_docx": "200"
            },
            {
                "key": "header_height",
                "type": "float",
                "description": "Specific height for the header image in pixels. Overrides header_size if set. Aspect ratio is maintained if only width or height is set.",
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
                "description": "Relative size of signature images as a percentage of their configured default dimensions (e.g., 80 for 80%).",
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
    for key, default_value in DEFAULT_STYLE_CONFIG.items():
        param_info = {"key": key}
        doc_variant_key = key + "_docx"
        is_docx_specific_key = key.endswith("_docx")
        has_docx_variant = doc_variant_key in DEFAULT_STYLE_CONFIG

        base_key_name = key[:-5] if is_docx_specific_key else key # e.g. title_font_size from title_font_size_docx

        # Description
        if is_docx_specific_key:
            param_info["description"] = f"DOCX specific: Styling for {base_key_name.replace('_', ' ')}."
        else:
            param_info["description"] = f"Styling for {key.replace('_', ' ')}. Primarily for PDF unless overridden by a DOCX-specific variant (e.g., '{key}_docx')."

        # Type, Examples, Notes
        if key.endswith("_color"):
            param_info["type"] = "string (color)"
            if is_docx_specific_key:
                param_info["example_pdf"] = "N/A"
                param_info["example_docx"] = str(default_value) + " (e.g., '#RRGGBB' or '000000')"
                param_info["notes"] = "DOCX: Expects hex color code (e.g., 'FF0000', '000000'). Service may map common color names."
            else:
                param_info["example_pdf"] = str(default_value) + " (e.g., '#RRGGBB' or color name like 'red')"
                param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value)) + " (Uses DOCX variant if available)"
                param_info["notes"] = "PDF: ReportLab color (hex, name). DOCX: Uses its own color system/variant. Service attempts to map."
        elif key.endswith("_font_family"):
            param_info["type"] = "string (font name)"
            if is_docx_specific_key:
                param_info["example_pdf"] = "N/A"
                param_info["example_docx"] = str(default_value)
                param_info["notes"] = "DOCX: System font name (e.g., 'Calibri', 'Times New Roman')."
            else:
                param_info["example_pdf"] = str(default_value)
                param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, "System default (e.g., Calibri)"))
                param_info["notes"] = "PDF: PostScript font name (e.g., 'Helvetica-Bold'). DOCX: Uses system font names (see DOCX variant or relies on adaptation)."
        elif key.endswith("_font_size") or "_leading" in key or key.endswith("_padding") or "_indent" in key or key.endswith("_thickness") or key.endswith("_same_line_max_length") or key.endswith("_space_after_docx") or key.endswith("_space_before_docx") or key.endswith("_docx_pt"): # Points
            param_info["type"] = "float or integer (points)"
            param_info["notes"] = "Units are typically points."
            if is_docx_specific_key:
                param_info["example_pdf"] = "N/A"
                param_info["example_docx"] = str(default_value)
            else:
                param_info["example_pdf"] = str(default_value)
                param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value)) + " (Uses DOCX variant if available, typically points)"
        elif key.startswith("page_margin_") or "_space_" in key or key.startswith("signature_image_") or key.endswith("_indent_docx"): # Inches (or adapted)
            param_info["type"] = "float (inches)"
            param_info["notes"] = "Units are typically inches. Service converts/adapts for the specific format (e.g., to Pt for some DOCX properties)."
            if is_docx_specific_key: # e.g. answer_left_indent_docx
                param_info["example_pdf"] = "N/A"
                param_info["example_docx"] = str(default_value)
            else:
                param_info["example_pdf"] = str(default_value)
                param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value)) + " (Uses DOCX variant if available, service converts units as needed)"
        elif key.endswith("_alignment"):
            param_info["type"] = "string or integer"
            param_info["notes"] = "Alignment values differ between PDF (ReportLab) and DOCX."
            if is_docx_specific_key:
                param_info["example_pdf"] = "N/A"
                param_info["example_docx"] = str(default_value) + " (e.g., 'left', 'center', 'right', 'justify')"
                param_info["accepted_values_docx"] = ["left", "center", "right", "justify"]
            else:
                param_info["example_pdf"] = str(default_value) + " (e.g., 'LEFT', 'CENTER', 0, 1, 2, 4)"
                param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, "center")) + " (Uses DOCX variant or adapted value)"
                param_info["accepted_values_pdf"] = ["LEFT", "CENTER", "RIGHT", "JUSTIFY", "0", "1", "2", "4"] # Strings to be safe
                param_info["accepted_values_docx"] = ["left", "center", "right", "justify"]
        elif key == "qa_layout":
            param_info["type"] = "string"
            param_info["accepted_values"] = ["answer_below", "answer_same_line"]
            param_info["example_pdf"] = str(default_value)
            param_info["example_docx"] = str(default_value)
            param_info["notes"] = "Determines if answers appear below questions or on the same line (if space permits)."
        else: # Generic fallback
            param_info["type"] = "string, float, or integer"
            param_info["example_pdf"] = str(default_value) if not callable(default_value) else "varies"
            param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value if not callable(default_value) else "varies"))
            param_info["notes"] = "Value type and interpretation may vary. Check service layer for specifics if unclear."
            if is_docx_specific_key:
                 param_info["example_pdf"] = "N/A"


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
        user_claims = current_user_identity 
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None


        pdf_data, metadata, error = ExportSubmissionController.generate_pdf_export(
            submission_id=submission_id,
            current_user=str(user_claims), 
            user_role=user_role
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
        user_claims = current_user_identity
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request)
        
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
    except ValueError as ve: 
        logger.warning(f"Validation error during custom PDF export for submission {submission_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error exporting custom PDF for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during PDF export"}), 500

@export_submission_bp.route('/<int:submission_id>/pdf/logo', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_custom_submission_to_pdf_logo(submission_id):
    """(DEPRECATED - Use /pdf/custom) Export a form submission as PDF with custom styling and options."""
    # This endpoint appears redundant with /pdf/custom. Consider removing or clearly differentiating.
    # For now, it behaves identically to /pdf/custom.
    try:
        current_user_identity = get_jwt_identity()
        user_claims = current_user_identity
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request)
        
        pdf_style_options = _extract_style_options(request.form)
        logger.debug(f"Custom PDF export (logo route): submission_id={submission_id}, style_options_count={len(pdf_style_options)}")

        pdf_data, metadata, error = ExportSubmissionController.generate_pdf_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role,
            header_image=common_params.get('header_image'), # This is where a logo would be passed
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
    except ValueError as ve:
        logger.warning(f"Validation error during custom PDF export (logo route) for submission {submission_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error exporting custom PDF (logo route) for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error during PDF export"}), 500

# --- DOCX Endpoints ---

@export_submission_bp.route('/<int:submission_id>/docx', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def export_default_submission_to_docx(submission_id):
    """Export a form submission as DOCX with default styling."""
    try:
        current_user_identity = get_jwt_identity()
        user_claims = current_user_identity
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        docx_data, metadata, error = ExportSubmissionController.generate_docx_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role
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
        user_claims = current_user_identity
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request)
        
        style_options = _extract_style_options(request.form)
        logger.debug(f"Custom DOCX export: submission_id={submission_id}, style_options_count={len(style_options)}")

        docx_data, metadata, error = ExportSubmissionController.generate_docx_export(
            submission_id=submission_id,
            current_user=str(user_claims),
            user_role=user_role,
            header_image=common_params.get('header_image'),
            header_size=common_params.get('header_size'), 
            header_width=common_params.get('header_width'),
            header_height=common_params.get('header_height'),
            header_alignment=common_params.get('header_alignment', "center"),
            signatures_size=common_params.get('signatures_size', 100),
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