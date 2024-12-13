from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_submission_controller import FormSubmissionController
from app.controllers.form_controller import FormController  # Added for form validation
from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

form_submission_bp = Blueprint('form_submissions', __name__)

# app/views/form_submission_views.py

@form_submission_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_submission():
    """Create a new form submission"""
    try:
        data = request.get_json()
        if not data or 'form_id' not in data:
            return jsonify({"error": "form_id is required"}), 400

        current_user = get_jwt_identity()
        submission, error = FormSubmissionController.create_submission(
            form_id=data['form_id'],
            username=current_user
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Form submission created successfully",
            "submission": submission.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating submission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_all_submissions():
    """Get all submissions with filters"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Build filters from query parameters
        filters = {}
        
        # Form filter
        form_id = request.args.get('form_id', type=int)
        if form_id:
            filters['form_id'] = form_id

        submissions = FormSubmissionController.get_all_submissions(user, filters)

        return jsonify([
            submission.to_dict() for submission in submissions
        ]), 200

    except Exception as e:
        logger.error(f"Error getting submissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submission(submission_id):
    """Get a specific submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        submission = FormSubmissionController.get_submission(submission_id)
        if not submission:
            return jsonify({"error": "Submission not found"}), 404

        # Access control
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(submission.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_submission(submission_id):
    """Delete a submission with cascade soft delete"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get submission checking is_deleted=False
        submission = FormSubmissionController.get_submission(submission_id)
        if not submission:
            return jsonify({"error": "Submission not found"}), 404

        # Access control
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                return jsonify({"error": "Cannot delete submissions by other users"}), 403

            # Check submission age for non-admin users
            submission_age = datetime.utcnow() - submission.submitted_at
            if submission_age.days > 7:  # Configurable timeframe
                return jsonify({
                    "error": "Cannot delete submissions older than 7 days"
                }), 400

        success, error = FormSubmissionController.delete_submission(submission_id)
        if success:
            return jsonify({
                "message": "Submission deleted successfully"
            }), 200
            
        return jsonify({"error": error}), 400

    except Exception as e:
        logger.error(f"Error deleting submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_form_submissions(form_id):
    """Get all submissions for a specific form"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Create filters for the specific form
        filters = {'form_id': form_id}

        submissions = FormSubmissionController.get_all_submissions(user, filters)

        return jsonify([
            submission.to_dict() for submission in submissions
        ]), 200

    except Exception as e:
        logger.error(f"Error getting submissions for form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/user/<string:username>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_user_submissions(username):
    """Get all submissions by a specific user"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Access control
        if not user.role.is_super_user and current_user != username:
            if user.role.name not in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                return jsonify({"error": "Unauthorized access"}), 403

        # Create filters for the specific user
        filters = {'submitted_by': username}
        
        submissions = FormSubmissionController.get_all_submissions(user, filters)

        return jsonify([
            submission.to_dict() for submission in submissions
        ]), 200

    except Exception as e:
        logger.error(f"Error getting submissions for user {username}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500