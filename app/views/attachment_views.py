from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.controllers.attachment_controller import AttachmentController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
import os

logger = logging.getLogger(__name__)

attachment_bp = Blueprint('attachments', __name__)

@attachment_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.ATTACHMENTS)
def create_attachment():
    """Create a new attachment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Validate form_submission_id
        form_submission_id = request.form.get('form_submission_id')
        if not form_submission_id:
            return jsonify({"error": "form_submission_id is required"}), 400

        # Validate file presence
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        is_signature = request.form.get('is_signature', '').lower() == 'true'

        attachment, error = AttachmentController.validate_and_create_attachment(
            form_submission_id=int(form_submission_id),
            file=file,
            current_user=current_user,
            is_signature=is_signature,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Attachment created successfully",
            "attachment": attachment
        }), 201

    except Exception as e:
        logger.error(f"Error creating attachment: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@attachment_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.ATTACHMENTS)
def bulk_create_attachments():
    """Bulk create attachments"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Validate form_submission_id
        form_submission_id = request.form.get('form_submission_id')
        if not form_submission_id:
            return jsonify({"error": "form_submission_id is required"}), 400
        
        # Get all files from the request
        files_data = []
        file_fields = [key for key in request.files.keys() if key.startswith('file')]
        
        if not file_fields:
            return jsonify({"error": "No files provided"}), 400
        
        for field in file_fields:
            file = request.files[field]
            if file and file.filename:
                # Get the index from the field name (e.g., 'file1' -> '1')
                index = field.replace('file', '')
                is_signature = request.form.get(f'is_signature{index}', '').lower() == 'true'
                
                files_data.append({
                    'file': file,
                    'is_signature': is_signature
                })
        
        if not files_data:
            return jsonify({"error": "No valid files provided"}), 400
        
        attachments, error = AttachmentController.bulk_create_attachments(
            form_submission_id=int(form_submission_id),
            files=files_data,
            current_user=current_user,
            user_role=user.role.name
        )
        
        if error:
            return jsonify({"error": error}), 400
        
        return jsonify({
            "message": "Attachments created successfully",
            "attachments": attachments
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating attachments: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@attachment_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def get_all_attachments():
    """Get all attachments with filtering"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Build filters from query parameters
        filters = {}
        
        # Form submission filter
        form_submission_id = request.args.get('form_submission_id', type=int)
        if form_submission_id:
            filters['form_submission_id'] = form_submission_id
        
        # Signature type filter
        is_signature = request.args.get('is_signature', type=lambda v: v.lower() == 'true')
        if is_signature is not None:
            filters['is_signature'] = is_signature
            
        # File type filter
        file_type = request.args.get('file_type')
        if file_type:
            filters['file_type'] = file_type
            
        attachments, error = AttachmentController.get_all_attachments(
            current_user=current_user,
            user_role=user.role.name,
            filters=filters
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({
            "total_count": len(attachments),
            "filters_applied": filters,
            "attachments": attachments
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting attachments: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/<int:attachment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def get_attachment(attachment_id):
    """Get and download a specific attachment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        attachment_data, error = AttachmentController.get_attachment_with_file(
            attachment_id=attachment_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 404 if error == "File not found" else 400

        # Return file for download
        return send_file(
            attachment_data['file_path'],
            mimetype=attachment_data['record'].file_type,
            as_attachment=True,
            download_name=attachment_data['filename']
        )

    except Exception as e:
        logger.error(f"Error retrieving attachment {attachment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/submission/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def get_submission_attachments(submission_id):
    """Get all attachments for a submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        attachments, error = AttachmentController.get_submission_attachments(
            submission_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            'submission_id': submission_id,
            'total_attachments': len(attachments),
            'attachments': attachments
        }), 200

    except Exception as e:
        logger.error(f"Error getting attachments for submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/<int:attachment_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.ATTACHMENTS)
def delete_attachment(attachment_id):
    """Delete an attachment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        success, message = AttachmentController.delete_attachment(
            attachment_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message,
            "deleted_id": attachment_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500