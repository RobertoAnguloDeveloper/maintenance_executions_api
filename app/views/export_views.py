from datetime import datetime
from flask import Blueprint, send_file, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.export_service import ExportService
from app.services.auth_service import AuthService
from app.controllers.form_controller import FormController
from app.utils.permission_manager import PermissionManager, EntityType
from io import BytesIO
import logging
import os

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)

DEFAULT_EXPORT_PARAMS = {
    'page_size': 'LETTER',
    'margin_top': 1.0,
    'margin_bottom': 1.0,
    'margin_left': 1.0,
    'margin_right': 1.0,
    'line_spacing': 1.15,
    'font_size': 12,
    'logo_path': None,
    'signatures': [
        {
            'title': 'Completed by',
            'name': '',
            'date': True
        },
        {
            'title': 'Reviewed by',
            'name': '',
            'date': True
        }
    ],
    'signature_spacing': {
        'before_section': 20,  # Space before signatures section
        'between_signatures': 10,  # Space between signatures
        'after_date': 5,  # Space after date field
        'after_section': 20  # Space after signatures section
    }
}

@export_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def export_form_data(form_id):
    """
    Export form data in specified format with custom formatting options
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404

        # Check access rights
        if not user.role.is_super_user:
            if not form.is_public and form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        # Get and validate format
        export_format = request.args.get('format', 'PDF').upper()
        export_service = ExportService()
        
        try:
            export_service.validate_format(export_format)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Get format parameters with defaults
        format_params = {
            'page_size': request.args.get('page_size', DEFAULT_EXPORT_PARAMS['page_size']).upper(),
            'margin_top': float(request.args.get('margin_top', DEFAULT_EXPORT_PARAMS['margin_top'])),
            'margin_bottom': float(request.args.get('margin_bottom', DEFAULT_EXPORT_PARAMS['margin_bottom'])),
            'margin_left': float(request.args.get('margin_left', DEFAULT_EXPORT_PARAMS['margin_left'])),
            'margin_right': float(request.args.get('margin_right', DEFAULT_EXPORT_PARAMS['margin_right'])),
            'line_spacing': float(request.args.get('line_spacing', DEFAULT_EXPORT_PARAMS['line_spacing'])),
            'font_size': int(request.args.get('font_size', DEFAULT_EXPORT_PARAMS['font_size'])),
            'logo_path': request.args.get('logo_path', DEFAULT_EXPORT_PARAMS['logo_path']),
            'signature_spacing': {
                'before_section': float(request.args.get('signature_space_before', DEFAULT_EXPORT_PARAMS['signature_spacing']['before_section'])),
                'between_signatures': float(request.args.get('signature_space_between', DEFAULT_EXPORT_PARAMS['signature_spacing']['between_signatures'])),
                'after_date': float(request.args.get('signature_space_date', DEFAULT_EXPORT_PARAMS['signature_spacing']['after_date'])),
                'after_section': float(request.args.get('signature_space_after', DEFAULT_EXPORT_PARAMS['signature_spacing']['after_section']))
            }
        }

        # Get signature parameters
        signatures = []
        signature_count = min(max(1, int(request.args.get('signature_count', 2))), 5)  # Between 1 and 5
        
        for i in range(signature_count):
            signature = {
                'title': request.args.get(
                    f'signature{i+1}_title',
                    DEFAULT_EXPORT_PARAMS['signatures'][i]['title'] if i < len(DEFAULT_EXPORT_PARAMS['signatures']) else f'Signature {i+1}'
                ),
                'name': request.args.get(f'signature{i+1}_name', ''),
                'date': request.args.get(f'signature{i+1}_date', 'true').lower() == 'true'
            }
            signatures.append(signature)

        format_params['signatures'] = signatures

        # Validate logo path if provided
        if format_params['logo_path']:
            if not os.path.exists(format_params['logo_path']):
                return jsonify({"error": "Logo file not found"}), 400
            if not format_params['logo_path'].lower().endswith(('.png', '.jpg', '.jpeg')):
                return jsonify({"error": "Logo must be PNG or JPG/JPEG format"}), 400

        # Prepare form data
        form_data = {
            'title': form.title,
            'description': form.description,
            'created_at': form.created_at.isoformat() if form.created_at else None,
            'updated_at': form.updated_at.isoformat() if form.updated_at else None,
            'created_by': {
                'id': form.creator.id,
                'username': form.creator.username,
                'email': form.creator.email,
                'first_name': form.creator.first_name,
                'last_name': form.creator.last_name,
                'fullname': f"{form.creator.first_name} {form.creator.last_name}",
                'environment': {
                    'id': form.creator.environment_id,
                    'name': form.creator.environment.name if form.creator.environment else None
                }
            },
            'is_public': form.is_public,
            'questions': [
                {
                    'id': q.question.id,
                    'form_question_id': q.id,
                    'text': q.question.text,
                    'type': q.question.question_type.type,
                    'order_number': q.order_number,
                    'remarks': q.question.remarks,
                    'possible_answers': [
                        {
                            'id': fa.answer.id,
                            'form_answer_id': fa.id,
                            'value': fa.answer.value
                        }
                        for fa in sorted(q.form_answers, key=lambda x: x.id)
                        if not fa.is_deleted and fa.answer and not fa.answer.is_deleted
                    ] if q.question.question_type.type in ['checkbox', 'multiple_choices'] else None
                }
                for q in sorted(form.form_questions, key=lambda x: x.order_number or 0)
                if not q.is_deleted and q.question and not q.question.is_deleted
            ]
        }

        # Generate export
        try:
            if export_format == 'PDF':
                file_data = export_service.export_as_pdf(form_data, format_params)
                mimetype = 'application/pdf'
                filename = f'form_{form_id}_{datetime.now().strftime("%Y%m%d")}.pdf'
            
            elif export_format == 'DOCX':
                file_data = export_service.export_as_docx(form_data, format_params)
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                filename = f'form_{form_id}_{datetime.now().strftime("%Y%m%d")}.docx'

            logger.info(f"Form {form_id} exported as {export_format} by user {current_user}")

            return send_file(
                BytesIO(file_data),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            logger.error(f"Error generating export: {str(e)}")
            return jsonify({
                "error": "Error generating export",
                "details": str(e)
            }), 500

    except Exception as e:
        logger.error(f"Error in export_form_data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@export_bp.route('/formats', methods=['GET'])
@jwt_required()
def get_supported_formats():
    """Get list of supported export formats"""
    try:
        formats = ExportService.get_supported_formats()
        return jsonify({
            "formats": formats,
            "default": "PDF"
        }), 200
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@export_bp.route('/parameters', methods=['GET'])
@jwt_required()
def get_format_parameters():
    """Get supported format parameters and their valid ranges"""
    return jsonify({
        "parameters": {
            "page_size": {
                "description": "Page size for the document",
                "values": ["A4", "LETTER", "LEGAL"],
                "default": DEFAULT_EXPORT_PARAMS['page_size']
            },
            "margin_top": {
                "description": "Top margin in inches",
                "range": [0.1, 3.0],
                "default": DEFAULT_EXPORT_PARAMS['margin_top']
            },
            "margin_bottom": {
                "description": "Bottom margin in inches",
                "range": [0.1, 3.0],
                "default": DEFAULT_EXPORT_PARAMS['margin_bottom']
            },
            "margin_left": {
                "description": "Left margin in inches",
                "range": [0.1, 3.0],
                "default": DEFAULT_EXPORT_PARAMS['margin_left']
            },
            "margin_right": {
                "description": "Right margin in inches",
                "range": [0.1, 3.0],
                "default": DEFAULT_EXPORT_PARAMS['margin_right']
            },
            "line_spacing": {
                "description": "Line spacing multiplier",
                "range": [1.0, 3.0],
                "default": DEFAULT_EXPORT_PARAMS['line_spacing']
            },
            "font_size": {
                "description": "Base font size in points",
                "range": [8, 16],
                "default": DEFAULT_EXPORT_PARAMS['font_size']
            },
            "signature_spacing": {
                "description": "Spacing configuration for signature section",
                "parameters": {
                    "signature_space_before": {
                        "description": "Space before signature section in points",
                        "range": [5, 50],
                        "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['before_section']
                    },
                    "signature_space_between": {
                        "description": "Space between signatures in points",
                        "range": [5, 30],
                        "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['between_signatures']
                    },
                    "signature_space_date": {
                        "description": "Space after date field in points",
                        "range": [2, 20],
                        "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['after_date']
                    },
                    "signature_space_after": {
                        "description": "Space after signature section in points",
                        "range": [5, 50],
                        "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['after_section']
                    }
                }
            },
            "logo_path": {
                "description": "Path to logo image file (PNG, JPG, JPEG)",
                "default": DEFAULT_EXPORT_PARAMS['logo_path']
            }
        }
    }), 200
    
@export_bp.route('/form/<int:form_id>/preview-params', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def preview_export_parameters(form_id):
    """
    Preview export parameters for a specific form
    """
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404

        # Check access rights
        if not user.role.is_super_user:
            if not form.is_public and form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        # Get current parameters from request or use defaults
        current_params = {
            'format': request.args.get('format', 'PDF').upper(),
            'page_size': request.args.get('page_size', DEFAULT_EXPORT_PARAMS['page_size']).upper(),
            'margin_top': float(request.args.get('margin_top', DEFAULT_EXPORT_PARAMS['margin_top'])),
            'margin_bottom': float(request.args.get('margin_bottom', DEFAULT_EXPORT_PARAMS['margin_bottom'])),
            'margin_left': float(request.args.get('margin_left', DEFAULT_EXPORT_PARAMS['margin_left'])),
            'margin_right': float(request.args.get('margin_right', DEFAULT_EXPORT_PARAMS['margin_right'])),
            'line_spacing': float(request.args.get('line_spacing', DEFAULT_EXPORT_PARAMS['line_spacing'])),
            'font_size': int(request.args.get('font_size', DEFAULT_EXPORT_PARAMS['font_size'])),
            'logo_path': request.args.get('logo_path', DEFAULT_EXPORT_PARAMS['logo_path']),
            'signature_spacing': {
                'before_section': float(request.args.get('signature_space_before', DEFAULT_EXPORT_PARAMS['signature_spacing']['before_section'])),
                'between_signatures': float(request.args.get('signature_space_between', DEFAULT_EXPORT_PARAMS['signature_spacing']['between_signatures'])),
                'after_date': float(request.args.get('signature_space_date', DEFAULT_EXPORT_PARAMS['signature_spacing']['after_date'])),
                'after_section': float(request.args.get('signature_space_after', DEFAULT_EXPORT_PARAMS['signature_spacing']['after_section']))
            }
        }

        # Build example URLs
        base_url = request.url_root.rstrip('/')
        example_urls = {
            'minimal': f"{base_url}/api/export/form/{form_id}?format=pdf",
            'with_basic_formatting': (
                f"{base_url}/api/export/form/{form_id}?"
                f"format=pdf&page_size=A4&margin_top=1.0&margin_bottom=1.0"
            ),
            'complete': (
                f"{base_url}/api/export/form/{form_id}?"
                f"format=pdf&"
                f"page_size=A4&"
                f"margin_top=1.5&"
                f"margin_bottom=1.5&"
                f"margin_left=1.0&"
                f"margin_right=1.0&"
                f"line_spacing=1.5&"
                f"font_size=12&"
                f"logo_path=/path/to/logo.png&"
                f"signature_space_before=1.0&"
                f"signature_space_between=8&"
                f"signature_space_date=1&"
                f"signature_space_after=0"
            )
        }

        return jsonify({
            "form_info": {
                "id": form.id,
                "title": form.title,
                "questions_count": len([q for q in form.form_questions if not q.is_deleted])
            },
            "current_parameters": current_params,
            "available_parameters": {
                "format": {
                    "description": "Export format",
                    "values": ["PDF", "DOCX"],
                    "default": "PDF",
                    "current": current_params['format']
                },
                "page_size": {
                    "description": "Page size for the document",
                    "values": ["A4", "LETTER", "LEGAL"],
                    "default": DEFAULT_EXPORT_PARAMS['page_size'],
                    "current": current_params['page_size']
                },
                "margin_top": {
                    "description": "Top margin in inches",
                    "range": [0.1, 3.0],
                    "default": DEFAULT_EXPORT_PARAMS['margin_top'],
                    "current": current_params['margin_top']
                },
                "margin_bottom": {
                    "description": "Bottom margin in inches",
                    "range": [0.1, 3.0],
                    "default": DEFAULT_EXPORT_PARAMS['margin_bottom'],
                    "current": current_params['margin_bottom']
                },
                "margin_left": {
                    "description": "Left margin in inches",
                    "range": [0.1, 3.0],
                    "default": DEFAULT_EXPORT_PARAMS['margin_left'],
                    "current": current_params['margin_left']
                },
                "margin_right": {
                    "description": "Right margin in inches",
                    "range": [0.1, 3.0],
                    "default": DEFAULT_EXPORT_PARAMS['margin_right'],
                    "current": current_params['margin_right']
                },
                "line_spacing": {
                    "description": "Line spacing multiplier",
                    "range": [1.0, 3.0],
                    "default": DEFAULT_EXPORT_PARAMS['line_spacing'],
                    "current": current_params['line_spacing']
                },
                "font_size": {
                    "description": "Base font size in points",
                    "range": [8, 16],
                    "default": DEFAULT_EXPORT_PARAMS['font_size'],
                    "current": current_params['font_size']
                },
                "signature_spacing": {
                    'before_section': {
                        "description":"before_section in points",
                        "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['before_section'],
                        "current": current_params['signature_spacing']['before_section']
                        },
                     'between_signatures': {
                          "description":"between_signatures in points",
                           "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['between_signatures'],
                           "current": current_params['signature_spacing']['between_signatures']
                     },
                     'after_date': {
                          "description":"after_date in points",
                           "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['after_date'],
                           "current": current_params['signature_spacing']['after_date']
                     },
                     'after_section':{
                          "description":"after_section in points",
                          "default": DEFAULT_EXPORT_PARAMS['signature_spacing']['after_section']
                     }
                },
                "logo_path": {
                    "description": "Path to logo image file (PNG, JPG, JPEG)",
                    "default": None,
                    "current": current_params['logo_path']
                }
            },
            "example_urls": example_urls,
            "notes": [
                "All margins are specified in inches",
                "Line spacing is a multiplier (1.0 = single spacing, 2.0 = double spacing)",
                "Font size is in points",
                "Logo must be in PNG or JPG/JPEG format"
            ]
        }), 200

    except Exception as e:
        logger.error(f"Error in preview_export_parameters: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500