from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.attachment_controller import AttachmentController

attachment_bp = Blueprint('attachments', __name__)

@attachment_bp.route('', methods=['POST'])
@jwt_required()
def create_attachment():
    data = request.get_json()
    form_submission_id = data.get('form_submission_id')
    file_type = data.get('file_type')
    file_path = data.get('file_path')
    file_name = data.get('file_name')
    file_size = data.get('file_size')
    is_signature = data.get('is_signature', False)

    if not all([form_submission_id, file_type, file_path, file_name, file_size]):
        return jsonify({"error": "Missing required fields"}), 400

    new_attachment, error = AttachmentController.create_attachment(
        form_submission_id, file_type, file_path, file_name, file_size, is_signature
    )
    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Attachment created successfully", "attachment": new_attachment.to_dict()}), 201

@attachment_bp.route('/<int:attachment_id>', methods=['GET'])
@jwt_required()
def get_attachment(attachment_id):
    attachment = AttachmentController.get_attachment(attachment_id)
    if attachment:
        return jsonify(attachment.to_dict()), 200
    return jsonify({"error": "Attachment not found"}), 404

@attachment_bp.route('/submission/<int:form_submission_id>', methods=['GET'])
@jwt_required()
def get_attachments_by_submission(form_submission_id):
    attachments = AttachmentController.get_attachments_by_submission(form_submission_id)
    return jsonify([attachment.to_dict() for attachment in attachments]), 200

@attachment_bp.route('/<int:attachment_id>', methods=['PUT'])
@jwt_required()
def update_attachment(attachment_id):
    data = request.get_json()
    updated_attachment, error = AttachmentController.update_attachment(attachment_id, **data)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"message": "Attachment updated successfully", "attachment": updated_attachment.to_dict()}), 200

@attachment_bp.route('/<int:attachment_id>', methods=['DELETE'])
@jwt_required()
def delete_attachment(attachment_id):
    success, error = AttachmentController.delete_attachment(attachment_id)
    if success:
        return jsonify({"message": "Attachment deleted successfully"}), 200
    return jsonify({"error": error}), 404