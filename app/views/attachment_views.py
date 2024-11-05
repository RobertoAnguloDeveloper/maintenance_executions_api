from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.attachment_controller import AttachmentController
from app.controllers.form_submission_controller import FormSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
import os

logger = logging.getLogger(__name__)

attachment_bp = Blueprint('attachments', __name__)

# ... [Previous routes remain the same] ...

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

        stats = AttachmentController.get_attachments_stats(form_submission_id)
        if not stats:
            return jsonify({"error": "Error generating statistics"}), 400

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

        attachment = AttachmentController.get_attachment(attachment_id)
        if not attachment:
            return jsonify({"error": "Attachment not found"}), 404

        # Check access rights
        if not user.role.is_super_user:
            submission = attachment.form_submission
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
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

        submission = FormSubmissionController.get_submission(form_submission_id)
        if not submission:
            return jsonify({"error": "Form submission not found"}), 404

        # Check access rights
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        signature = AttachmentController.get_signature_attachment(form_submission_id)
        if not signature:
            return jsonify({"error": "Signature not found"}), 404

        # Check if the file exists
        if not os.path.exists(signature.file_path):
            return jsonify({"error": "Signature file not found"}), 404

        return send_file(
            signature.file_path,
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

        attachment_ids = data['attachment_ids']
        results = {
            'successful': [],
            'failed': []
        }

        for attachment_id in attachment_ids:
            attachment = AttachmentController.get_attachment(attachment_id)
            if not attachment:
                results['failed'].append({
                    'id': attachment_id,
                    'error': 'Attachment not found'
                })
                continue

            # Check access rights
            if not user.role.is_super_user:
                submission = attachment.form_submission
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != user.environment_id:
                        results['failed'].append({
                            'id': attachment_id,
                            'error': 'Unauthorized access'
                        })
                        continue
                elif submission.submitted_by != current_user:
                    results['failed'].append({
                        'id': attachment_id,
                        'error': 'Unauthorized access'
                    })
                    continue

            success, error = AttachmentController.delete_attachment(attachment_id)
            if success:
                results['successful'].append(attachment_id)
            else:
                results['failed'].append({
                    'id': attachment_id,
                    'error': error
                })

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