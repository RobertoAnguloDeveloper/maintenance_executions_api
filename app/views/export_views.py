from flask import Blueprint, send_file, request
from flask_jwt_extended import jwt_required
from app.services.export_service import ExportService

export_bp = Blueprint('export', __name__)

@export_bp.route('/export/<int:form_id>', methods=['GET'])
@jwt_required()
def export_form_data(form_id):
    format = request.args.get('format', 'csv')
    file_path = ExportService.export_form_data(form_id, format)
    return send_file(file_path, as_attachment=True)