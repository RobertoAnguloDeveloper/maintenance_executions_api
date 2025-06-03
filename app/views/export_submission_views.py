# app/views/export_submission_views.py

from flask import Blueprint, request, send_file, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.export_submission_controller import ExportSubmissionController
# Assuming AuthService and PermissionManager are correctly set up and imported elsewhere if needed by decorators
# from app.services.auth_service import AuthService 
# from app.utils.permission_manager import PermissionManager, EntityType 
from app.services.export_submission_service import DEFAULT_STYLE_CONFIG, _parse_numeric_value # Import for style keys
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

export_submission_bp = Blueprint('export_submissions', __name__, url_prefix='/api/export_submissions')

def _extract_style_options(source_data): # source_data is request.form
    style_options = {}
    for key in DEFAULT_STYLE_CONFIG.keys():
        if key in source_data and source_data[key] is not None and source_data[key] != '':
            style_options[key] = source_data[key]
    return style_options

def _parse_common_export_params(current_request):
    """Helper to parse common parameters for custom exports from the Flask request object."""
    params = {}
    params['header_image'] = current_request.files.get('header_image')

    if params['header_image']:
        if not params['header_image'].filename or not params['header_image'].filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif')):
            raise ValueError("Header image must be PNG, JPG, JPEG, GIF, or SVG format.")

    form_data = current_request.form

    if 'header_opacity' in form_data and form_data['header_opacity']:
        try:
            opacity_value = float(form_data['header_opacity'])
            params['header_opacity'] = max(0.0, min(100.0, opacity_value)) / 100.0 
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

    # NEW: Parse signatures position alignment
    if 'signatures_position_alignment' in form_data and form_data['signatures_position_alignment']:
        sig_pos_alignment = form_data['signatures_position_alignment'].lower()
        valid_sig_pos_alignments = ['left', 'center', 'right']
        if sig_pos_alignment not in valid_sig_pos_alignments:
            raise ValueError(f"Invalid signatures position alignment. Must be one of: {', '.join(valid_sig_pos_alignments)}.")
        params['signatures_position_alignment'] = sig_pos_alignment

    if 'include_signatures' in form_data:
        params['include_signatures'] = form_data['include_signatures'].lower() in ['true', '1', 'yes', 'on']

    return params

@export_submission_bp.route('/customization_options', methods=['GET'])
def get_export_customization_options():
    """
    Provides a list of all accepted parameters for custom PDF and DOCX export requests.
    """
    options = {
        "common_options": [
            {"key": "header_image", "type": "file", "description": "Image file for the header.", "notes": "Supported: PNG, JPG, JPEG, GIF, SVG."},
            {"key": "header_opacity", "type": "float (0-100)", "description": "Header image opacity (PDF only).", "example_pdf": "80", "example_docx": "N/A"},
            {"key": "header_size", "type": "float (%)", "description": "Header image size percentage.", "example_pdf": "50", "example_docx": "50"},
            {"key": "header_width", "type": "float (px)", "description": "Header image width in pixels.", "example_pdf": "200", "example_docx": "200"},
            {"key": "header_height", "type": "float (px)", "description": "Header image height in pixels.", "example_pdf": "100", "example_docx": "100"},
            {"key": "header_alignment", "type": "string", "description": "Header image alignment.", "accepted_values": ["left", "center", "right"], "example_pdf": "center", "example_docx": "center"},
            {"key": "signatures_size", "type": "float (%)", "description": "Signature images size percentage.", "example_pdf": "80", "example_docx": "80"},
            {"key": "signatures_alignment", "type": "string", "description": "Layout for multiple signatures.", "accepted_values": ["vertical", "horizontal"], "example_pdf": "vertical", "example_docx": "vertical"},
            {"key": "signatures_position_alignment", "type": "string", "description": "Position alignment for signatures within their container.", "accepted_values": ["left", "center", "right"], "example_pdf": "center", "example_docx": "center"},  # NEW
            {"key": "include_signatures", "type": "boolean", "description": "Include signatures in export.", "accepted_values": ["true", "false", "1", "0"], "example_pdf": "true", "example_docx": "true"}
        ],
        "style_options": [] 
    }

    # Keys for PDF ParagraphStyle whose user-provided overrides should be in Points.
    # Their defaults in DEFAULT_STYLE_CONFIG are in Inches.
    pdf_style_spatial_keys_user_input_as_points = [
        "title_space_after", "description_space_after", "info_space_after",
        "question_left_indent", "question_space_before", "question_space_after",
        "answer_left_indent", "answer_space_before", "answer_space_after",
        "table_space_after"
    ]
    # Keys for PDF TableStyle which are always in Points.
    pdf_style_table_padding_keys = [
        "table_cell_padding_left", "table_cell_padding_right", 
        "table_cell_padding_top", "table_cell_padding_bottom", "table_grid_thickness"
    ]

    for key, default_value in DEFAULT_STYLE_CONFIG.items():
        param_info = {"key": key}
        doc_variant_key = key + "_docx"
        is_docx_specific_key = key.endswith("_docx")
        base_key_name = key[:-5] if is_docx_specific_key else key
        
        if is_docx_specific_key: param_info["description"] = f"DOCX specific: Styling for {base_key_name.replace('_', ' ')}."
        else: param_info["description"] = f"Styling for {key.replace('_', ' ')}."
        
        if key in ["signature_position_alignment", "signature_position_alignment_docx"]:
            param_info["type"] = "string"
            param_info["accepted_values"] = ["left", "center", "right"]
            param_info["example_pdf"] = "center"
            param_info["example_docx"] = "center"

        if key in pdf_style_spatial_keys_user_input_as_points:
            param_info["type"] = "float or integer (points)"
            param_info["notes"] = "For PDF, provide this override value in points. Default is calculated from inches in config."
            param_info["example_pdf"] = f"{_parse_numeric_value(default_value) * 72.0:.1f} (points, this is the default converted from inches)"
            param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, "N/A if not applicable"))
        elif key in pdf_style_table_padding_keys:
            param_info["type"] = "float or integer (points)"
            param_info["notes"] = "For PDF TableStyle, value is in points."
            param_info["example_pdf"] = str(default_value)
            param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value))
        elif key.endswith("_color"):
            param_info["type"] = "string (color)"; 
            if is_docx_specific_key: param_info["example_pdf"] = "N/A"; param_info["example_docx"] = str(default_value) + " (hex or name)"
            else: param_info["example_pdf"] = str(default_value) + " (hex, name, or ReportLab color)"; param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value))
        elif key.endswith("_font_family"):
            param_info["type"] = "string (font name)";
            if is_docx_specific_key: param_info["example_pdf"] = "N/A"; param_info["example_docx"] = str(default_value)
            else: param_info["example_pdf"] = str(default_value); param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, "System default"))
        elif key.endswith(("_font_size", "_leading", "_docx_pt")) or \
             (is_docx_specific_key and ("_space_" in key or "_indent" in key or "_padding" in key or "_thickness" in key)):
            param_info["type"] = "float or integer (points)"
            if is_docx_specific_key: param_info["example_pdf"] = "N/A"; param_info["example_docx"] = str(default_value)
            else: param_info["example_pdf"] = str(default_value); param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value))
        elif key.startswith("page_margin_") or key.startswith("signature_image_"): # These are in inches
            param_info["type"] = "float (inches)"
            param_info["notes"] = "Value in inches."
            param_info["example_pdf"] = str(default_value); param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value))
        elif key.endswith("_alignment"):
             param_info["type"] = "string or integer"; 
             if is_docx_specific_key: param_info["example_pdf"] = "N/A"; param_info["example_docx"] = str(default_value); param_info["accepted_values_docx"] = ["left", "center", "right", "justify"]
             else: param_info["example_pdf"] = str(default_value); param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, "center")); param_info["accepted_values_pdf"] = ["LEFT", "CENTER", "RIGHT", "JUSTIFY", "0", "1", "2", "4"]
        elif key == "qa_layout":
            param_info["type"] = "string"; param_info["accepted_values"] = ["answer_below", "answer_same_line"]; param_info["example_pdf"] = str(default_value); param_info["example_docx"] = str(default_value)
        else: 
            param_info["type"] = "string, float, or integer"; 
            param_info["example_pdf"] = str(default_value) if not callable(default_value) else "varies"
            param_info["example_docx"] = str(DEFAULT_STYLE_CONFIG.get(doc_variant_key, default_value if not callable(default_value) else "varies"))
            if is_docx_specific_key: param_info["example_pdf"] = "N/A"
        
        options["style_options"].append(param_info)
    return jsonify(options), 200

@export_submission_bp.route('/<int:submission_id>/<string:export_format>/custom', methods=['POST'])
@jwt_required()
def export_custom_submission(submission_id: int, export_format: str):
    """
    Export a form submission as PDF or DOCX with custom styling and options.
    <export_format> can be 'pdf' or 'docx'.
    """
    export_format = export_format.lower()
    if export_format not in ['pdf', 'docx']:
        return jsonify({"error": "Invalid export format specified. Must be 'pdf' or 'docx'."}), 400

    try:
        current_user_identity = get_jwt_identity()
        user_claims = current_user_identity 
        user_role = user_claims.get('role') if isinstance(user_claims, dict) else None

        common_params = _parse_common_export_params(request)
        style_options = _extract_style_options(request.form)
        
        logger.debug(f"Custom {export_format.upper()} export: submission_id={submission_id}, common_params_keys={list(common_params.keys())}, style_options_count={len(style_options)}")

        data_buffer = None
        metadata = None
        error = None

        if export_format == 'pdf':
            data_buffer, metadata, error = ExportSubmissionController.generate_pdf_export(
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
                signatures_position_alignment=common_params.get('signatures_position_alignment', "center"),  # NEW
                include_signatures=common_params.get('include_signatures', True),
                pdf_style_options=style_options
            )
        elif export_format == 'docx':
            data_buffer, metadata, error = ExportSubmissionController.generate_docx_export(
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
                signatures_position_alignment=common_params.get('signatures_position_alignment', "center"),  # NEW
                include_signatures=common_params.get('include_signatures', True),
                style_options=style_options
            )

        if error:
            return jsonify({"error": error}), 400 if "not found" in error.lower() or "Invalid" in error else 500
        
        if not data_buffer or not metadata:
             return jsonify({"error": f"Failed to generate {export_format.upper()} file."}), 500

        return send_file(
            BytesIO(data_buffer), 
            mimetype=metadata["mimetype"],
            as_attachment=True,
            download_name=metadata["filename"]
        )
    except ValueError as ve: 
        logger.warning(f"Validation error during custom {export_format.upper()} export for submission {submission_id}: {str(ve)}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error exporting custom {export_format.upper()} for submission {submission_id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error during {export_format.upper()} export"}), 500

@export_submission_bp.route('/<int:submission_id>/pdf', methods=['GET'])
@jwt_required()
# @PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
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

@export_submission_bp.route('/<int:submission_id>/docx', methods=['GET'])
@jwt_required()
# @PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
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

@export_submission_bp.route('/<int:submission_id>/<string:export_format>/logo', methods=['POST'])
@jwt_required()
# @PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS) 
def export_custom_submission_with_logo(submission_id: int, export_format: str):
    """
    (CONSIDER DEPRECATING in favor of /custom) 
    Export a form submission with custom options, ensuring header_image (logo) is handled.
    """
    logger.info(f"Accessing /logo endpoint for submission {submission_id}, format {export_format}. Consider using /custom.")
    export_format_lower = export_format.lower()
    if export_format_lower not in ['pdf', 'docx']:
        return jsonify({"error": "Invalid export format specified for /logo endpoint. Must be 'pdf' or 'docx'."}), 400
    
    return export_custom_submission(submission_id, export_format_lower)