# app/views/attachment_views.py

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.attachment_controller import AttachmentController
from app.controllers.form_submission_controller import FormSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
from werkzeug.utils import secure_filename
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

attachment_bp = Blueprint('attachments', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(file):
    """Get file size in bytes"""
    file.seek(0, 2)  # Seek to end of file
    size = file.tell()  # Get current position (size)
    file.seek(0)  # Reset file position
    return size

@attachment_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.ATTACHMENTS)
def create_attachment():
    """Create a new attachment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Validate file presence
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Validate form submission ID
        form_submission_id = request.form.get('form_submission_id')
        if not form_submission_id:
            return jsonify({"error": "form_submission_id is required"}), 400

        try:
            form_submission_id = int(form_submission_id)
        except ValueError:
            return jsonify({"error": "form_submission_id must be a number"}), 400

        # Validate form submission exists and check access rights
        submission_result = FormSubmissionController.get_submission(form_submission_id)
        if not submission_result:
            return jsonify({"error": "Error retrieving form submission"}), 500
            
        submission, error = submission_result
        if error:
            return jsonify({"error": error}), 404

        if not submission:
            return jsonify({"error": "Form submission not found"}), 404

        # Check access rights
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                
                # Create user directory structure
                user_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.username)
                date_path = os.path.join(user_path, datetime.now().strftime('%Y/%m/%d'))
                os.makedirs(date_path, exist_ok=True)
                
                # Create unique filename if needed
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(date_path, filename)):
                    filename = f"{base}_{counter}{ext}"
                    counter += 1

                # Save file
                file_path = os.path.join(date_path, filename)
                file.save(file_path)
                
                # Get relative path for database
                relative_path = os.path.relpath(file_path, current_app.config['UPLOAD_FOLDER'])

                # Create attachment record
                attachment_result = AttachmentController.create_attachment(
                    form_submission_id=form_submission_id,
                    file_type=file.content_type,
                    file_path=relative_path,
                    file_name=filename,
                    file_size=get_file_size(file),
                    is_signature=request.form.get('is_signature', 'false').lower() == 'true'
                )

                if not attachment_result:
                    # Clean up file if database insert failed
                    os.remove(file_path)
                    return jsonify({"error": "Error creating attachment record"}), 500

                new_attachment, error = attachment_result
                if error:
                    # Clean up file if database insert failed
                    os.remove(file_path)
                    return jsonify({"error": error}), 400

                logger.info(f"Attachment created by user {user.username}")
                return jsonify({
                    "message": "Attachment created successfully",
                    "attachment": new_attachment.to_dict()
                }), 201

            except OSError as e:
                logger.error(f"File system error: {str(e)}")
                return jsonify({"error": f"Error saving file: {str(e)}"}), 500

        return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        logger.error(f"Error creating attachment: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/stats', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def get_attachment_stats():
    """Get attachment statistics"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        form_submission_id = request.args.get('form_submission_id', type=int)
        
        # If form_submission_id provided, check access
        if form_submission_id:
            submission = FormSubmissionController.get_submission(form_submission_id)
            if not submission:
                return jsonify({"error": "Form submission not found"}), 404

            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != user.environment_id:
                        return jsonify({"error": "Unauthorized access"}), 403
                elif submission.submitted_by != current_user:
                    return jsonify({"error": "Unauthorized access"}), 403

        stats, error = AttachmentController.get_attachments_stats(form_submission_id)
        if error:
            return jsonify({"error": error}), 400

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting attachment statistics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/<int:attachment_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.ATTACHMENTS)
def update_attachment(attachment_id):
    """Update attachment details"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        attachment, error = AttachmentController.get_attachment(attachment_id)
        if error:
            return jsonify({"error": error}), 404

        # Check access rights
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if attachment.form_submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif attachment.form_submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        allowed_fields = ['file_type', 'is_signature']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        updated_attachment, error = AttachmentController.update_attachment(
            attachment_id,
            **update_data
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Attachment {attachment_id} updated by user {current_user}")
        return jsonify({
            "message": "Attachment updated successfully",
            "attachment": updated_attachment.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating attachment {attachment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/signature/<int:form_submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def get_signature(form_submission_id):
    """Get signature attachment for a form submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the submission
        submission = FormSubmissionController.get_submission(form_submission_id)
        if not submission:
            return jsonify({"error": "Form submission not found"}), 404

        # Access control
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        signature, error = AttachmentController.get_signature_attachment(form_submission_id)
        if error:
            return jsonify({"error": error}), 404

        # Get full file path
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], signature.file_path)
        if not os.path.exists(file_path):
            return jsonify({"error": "Signature file not found"}), 404

        return send_file(
            file_path,
            mimetype=signature.file_type,
            as_attachment=True,
            download_name=f"signature_{form_submission_id}{os.path.splitext(signature.file_path)[1]}"
        )

    except Exception as e:
        logger.error(f"Error getting signature for submission {form_submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/bulk-delete', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.ATTACHMENTS)
def bulk_delete_attachments():
    """Delete multiple attachments"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if not data or 'attachment_ids' not in data:
            return jsonify({"error": "No attachment IDs provided"}), 400

        results, error = AttachmentController.bulk_delete_attachments(data['attachment_ids'])
        if error:
            return jsonify({"error": error}), 400

        if not results['failed']:
            logger.info(f"Bulk deletion of attachments completed successfully by user {current_user}")
            return jsonify({
                "message": "All attachments deleted successfully",
                "deleted_count": len(results['successful'])
            }), 200

        if not results['successful']:
            return jsonify({
                "error": "All deletions failed",
                "failures": results['failed']
            }), 400

        logger.warning(f"Partial success in bulk deletion by user {current_user}")
        return jsonify({
            "message": "Some attachments were deleted successfully",
            "successful_count": len(results['successful']),
            "failed_count": len(results['failed']),
            "failures": results['failed']
        }), 207

    except Exception as e:
        logger.error(f"Error in bulk attachment deletion: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/<int:attachment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def get_attachment(attachment_id):
    """Get and download an attachment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        attachment, error = AttachmentController.get_attachment(attachment_id)
        if error:
            return jsonify({"error": error}), 404

        # Check access rights
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if attachment.form_submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif attachment.form_submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment.file_path)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        return send_file(
            file_path,
            mimetype=attachment.file_type,
            as_attachment=True,
            download_name=os.path.basename(attachment.file_path)
        )

    except Exception as e:
        logger.error(f"Error retrieving attachment {attachment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@attachment_bp.route('/<int:attachment_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.ATTACHMENTS)
def delete_attachment(attachment_id):
    """Delete an attachment with associated file"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get attachment checking is_deleted=False
        attachment = AttachmentController.get_attachment(attachment_id)
        if not attachment:
            return jsonify({"error": "Attachment not found"}), 404

        # Access control
        if not user.role.is_super_user:
            # Site Managers and Supervisors can delete in their environment
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if attachment.form_submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            # Technicians can only delete their own attachments
            elif attachment.form_submission.submitted_by != current_user:
                return jsonify({"error": "Cannot delete attachments from other users"}), 403

            # Check submission age for non-admin users
            submission_age = datetime.utcnow() - attachment.form_submission.submitted_at
            if submission_age.days > 7:  # Configurable timeframe
                return jsonify({
                    "error": "Cannot delete attachments from submissions older than 7 days"
                }), 400

        # Prevent deletion of signature attachments by non-admins
        if attachment.is_signature and not user.role.is_super_user:
            return jsonify({"error": "Only administrators can delete signature attachments"}), 403

        success, result = AttachmentController.delete_attachment(attachment_id)
        if success:
            logger.info(f"Attachment {attachment_id} deleted by {user.username}")
            return jsonify({
                "message": "Attachment deleted successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500