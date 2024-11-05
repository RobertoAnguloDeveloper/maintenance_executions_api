# app/views/answer_submitted_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.answer_submitted_controller import AnswerSubmittedController
from app.controllers.form_submission_controller import FormSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

answer_submitted_bp = Blueprint('answers_submitted', __name__)

@answer_submitted_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_answer_submitted():
    """Create a new submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        required_fields = ['form_answer_id', 'form_submission_id']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate form submission ownership
        if not user.role.is_super_user:
            form_submission = FormSubmissionController.get_form_submission(data['form_submission_id'])
            if not form_submission or form_submission.submitted_by != user.username:
                return jsonify({"error": "Unauthorized access"}), 403

        new_answer_submitted, error = AnswerSubmittedController.create_answer_submitted(
            form_answer_id=data['form_answer_id'],
            form_submission_id=data['form_submission_id']
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Answer submitted by user {user.username}")
        return jsonify({
            "message": "Answer submitted successfully",
            "answer_submitted": new_answer_submitted.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/submission/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_answers_by_submission(submission_id):
    """Get all submitted answers for a form submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Validate form submission access
        form_submission = FormSubmissionController.get_form_submission(submission_id)
        if not form_submission:
            return jsonify({"error": "Form submission not found"}), 404

        if not user.role.is_super_user:
            if form_submission.submitted_by != user.username and \
               form_submission.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        submitted_answers = AnswerSubmittedController.get_answers_by_submission(submission_id)
        return jsonify([answer.to_dict() for answer in submitted_answers]), 200

    except Exception as e:
        logger.error(f"Error getting submitted answers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_answer_submitted(answer_submitted_id):
    """Get a specific submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answer_submitted = AnswerSubmittedController.get_answer_submitted(answer_submitted_id)
        if not answer_submitted:
            return jsonify({"error": "Submitted answer not found"}), 404

        # Check access
        if not user.role.is_super_user:
            if answer_submitted.form_submission.submitted_by != user.username and \
               answer_submitted.form_submission.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(answer_submitted.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting submitted answer {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_answer_submitted(answer_submitted_id):
    """Delete a submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answer_submitted = AnswerSubmittedController.get_answer_submitted(answer_submitted_id)
        if not answer_submitted:
            return jsonify({"error": "Submitted answer not found"}), 404

        # Check access
        if not user.role.is_super_user:
            if answer_submitted.form_submission.submitted_by != user.username:
                return jsonify({"error": "Unauthorized access"}), 403

        success, error = AnswerSubmittedController.delete_answer_submitted(answer_submitted_id)
        if success:
            logger.info(f"Submitted answer {answer_submitted_id} deleted by user {user.username}")
            return jsonify({"message": "Submitted answer deleted successfully"}), 200
        return jsonify({"error": error}), 404

    except Exception as e:
        logger.error(f"Error deleting submitted answer {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500