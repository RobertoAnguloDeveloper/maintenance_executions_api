from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_submission_controller import FormSubmissionController
from app.controllers.form_controller import FormController  # Added for form validation
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

form_submission_bp = Blueprint('form_submissions', __name__)

@form_submission_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_submission():
    """Create a new form submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if not data or 'form_id' not in data or 'answers' not in data:
            return jsonify({
                "error": "Missing required fields"
            }), 400

        # Validate form access
        form = FormController.get_form(data['form_id'])
        if not form:
            return jsonify({"error": "Form not found"}), 404

        if not form.is_public and not user.role.is_super_user:
            if form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access to form"}), 403

        submission, error = FormSubmissionController.create_submission(
            form_id=data['form_id'],
            username=current_user,
            answers_data=data['answers'],
            attachments_data=data.get('attachments')
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Form submission created by user {current_user}")
        return jsonify({
            "message": "Form submitted successfully",
            "submission": submission.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating submission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submissions():
    """Get submissions with filters"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get query parameters
        form_id = request.args.get('form_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Parse dates if provided
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Handle different roles
        if user.role.is_super_user:
            # Admins can see all submissions
            submissions = FormSubmissionController.get_submissions_by_form(form_id)
        elif user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
            # Site Managers and Supervisors see submissions in their environment
            submissions = FormSubmissionController.get_submissions_by_environment(
                user.environment_id, form_id
            )
        else:
            # Regular users only see their own submissions
            submissions = FormSubmissionController.get_submissions_by_user(
                current_user, form_id, start_date, end_date
            )

        return jsonify([submission.to_dict() for submission in submissions]), 200

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

@form_submission_bp.route('/<int:submission_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.SUBMISSIONS)
def update_submission(submission_id):
    """Update a submission"""
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

        data = request.get_json()
        updated_submission, error = FormSubmissionController.update_submission(
            submission_id,
            answers_data=data.get('answers'),
            attachments_data=data.get('attachments')
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Submission {submission_id} updated by user {current_user}")
        return jsonify({
            "message": "Submission updated successfully",
            "submission": updated_submission.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_submission(submission_id):
    """Delete a submission"""
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

        success, error = FormSubmissionController.delete_submission(submission_id)
        if success:
            logger.info(f"Submission {submission_id} deleted by user {current_user}")
            return jsonify({"message": "Submission deleted successfully"}), 200
        return jsonify({"error": error}), 400

    except Exception as e:
        logger.error(f"Error deleting submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/statistics', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submission_statistics():
    """Get submission statistics"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get query parameters
        form_id = request.args.get('form_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        date_range = None
        if start_date and end_date:
            date_range = {
                'start': datetime.strptime(start_date, '%Y-%m-%d'),
                'end': datetime.strptime(end_date, '%Y-%m-%d')
            }

        # Handle different roles
        if user.role.is_super_user:
            stats = FormSubmissionController.get_submission_statistics(
                form_id=form_id,
                date_range=date_range
            )
        else:
            stats = FormSubmissionController.get_submission_statistics(
                form_id=form_id,
                environment_id=user.environment_id,
                date_range=date_range
            )

        if not stats:
            return jsonify({"error": "Error generating statistics"}), 400

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting submission statistics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500