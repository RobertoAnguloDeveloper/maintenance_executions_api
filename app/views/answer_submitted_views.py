from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.auth_service import AuthService
from app.controllers.answer_submitted_controller import AnswerSubmittedController
from app.controllers.form_submission_controller import FormSubmissionController
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

answer_submitted_bp = Blueprint('answers-submitted', __name__)

@answer_submitted_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_answer_submitted():
    """Create a new submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['form_answers_id', 'form_submissions_id']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": "Missing required fields",
                "required_fields": required_fields
            }), 400

        # Validate form submission ownership
        submission = FormSubmissionController.get_submission(data['form_submissions_id'])
        if not submission:
            return jsonify({"error": "Form submission not found"}), 404

        if not user.role.is_super_user:
            if submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access to form submission"}), 403

        # Create the answer submission
        answer_submitted, error = AnswerSubmittedController.create_answer_submitted(
            form_answers_id=data['form_answers_id'],
            form_submissions_id=data['form_submissions_id'],
            text_answered=data.get('text_answered')
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Answer submitted successfully",
            "answer_submitted": answer_submitted
        }), 201

    except Exception as e:
        logger.error(f"Error creating answer submission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_all_answers_submitted():
    """Get all answers submitted with filters"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Build filters from query parameters
        filters = {}
        
        # Form filter
        form_id = request.args.get('form_id', type=int)
        if form_id:
            filters['form_id'] = form_id

        # Date range filters
        start_date = request.args.get('start_date')
        if start_date:
            try:
                filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

        end_date = request.args.get('end_date')
        if end_date:
            try:
                filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

        answers_submitted = AnswerSubmittedController.get_all_answers_submitted(user, filters)

        return jsonify({
            'total_count': len(answers_submitted),
            'filters_applied': filters,
            'answers_submitted': answers_submitted
        }), 200

    except Exception as e:
        logger.error(f"Error getting answers submitted: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_answer_submitted(answer_submitted_id):
    """Get a specific submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answer_submitted, error = AnswerSubmittedController.get_answer_submitted(answer_submitted_id)
        if error:
            return jsonify({"error": error}), 404

        # Access control
        if not user.role.is_super_user:
            submission = FormSubmissionController.get_submission(answer_submitted['form_submissions_id'])
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(answer_submitted), 200

    except Exception as e:
        logger.error(f"Error getting answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.SUBMISSIONS)
def update_answer_submitted(answer_submitted_id):
    """Update a submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get current answer submission
        current_answer, error = AnswerSubmittedController.get_answer_submitted(answer_submitted_id)
        if error:
            return jsonify({"error": error}), 404

        # Access control
        if not user.role.is_super_user:
            submission = FormSubmissionController.get_submission(current_answer['form_submissions_id'])
            if submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        updated_answer, error = AnswerSubmittedController.update_answer_submitted(
            answer_submitted_id,
            text_answered=data.get('text_answered')
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Answer submission updated successfully",
            "answer_submitted": updated_answer
        }), 200

    except Exception as e:
        logger.error(f"Error updating answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_answer_submitted(answer_submitted_id):
    """Delete a submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get current answer submission
        current_answer, error = AnswerSubmittedController.get_answer_submitted(answer_submitted_id)
        if error:
            return jsonify({"error": error}), 404

        # Access control
        if not user.role.is_super_user:
            submission = FormSubmissionController.get_submission(current_answer['form_submissions_id'])
            if submission.submitted_by != current_user:
                return jsonify({"error": "Unauthorized access"}), 403

        success, message = AnswerSubmittedController.delete_answer_submitted(answer_submitted_id)
        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message,
            "deleted_id": answer_submitted_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500