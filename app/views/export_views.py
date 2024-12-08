# app/views/export_views.py

from datetime import datetime
from flask import Blueprint, send_file, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.export_service import ExportService
from app.services.auth_service import AuthService
from app.controllers.form_controller import FormController
from app.utils.permission_manager import PermissionManager, EntityType
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)

@export_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def export_form_data(form_id):
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
        export_format = request.args.get('format', 'csv').upper()
        export_service = ExportService()
        
        try:
            export_service.validate_format(export_format)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Prepare form data for export with your specific structure
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
            'submissions_count': len([s for s in form.submissions if not s.is_deleted]),
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

        # Generate export based on format
        try:
            if export_format in ['PNG', 'JPG']:
                file_data = export_service.export_as_image(form_data, format=export_format)
                mimetype = f'image/{export_format.lower()}'
                filename = f'form_{form_id}_{datetime.now().strftime("%Y%m%d")}.{export_format.lower()}'
            
            elif export_format == 'PDF':
                file_data = export_service.export_as_pdf(form_data)
                mimetype = 'application/pdf'
                filename = f'form_{form_id}_{datetime.now().strftime("%Y%m%d")}.pdf'
            
            elif export_format == 'DOCX':
                file_data = export_service.export_as_docx(form_data)
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                filename = f'form_{form_id}_{datetime.now().strftime("%Y%m%d")}.docx'
            
            else:
                return jsonify({
                    "error": f"Export format {export_format} not yet implemented"
                }), 501

            # Log export attempt
            logger.info(
                f"Form {form_id} exported as {export_format} by user {current_user}"
            )

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
            "default": "csv"
        }), 200
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500