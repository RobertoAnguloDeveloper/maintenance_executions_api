# app/views/answer_submitted_views.py

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.answer_submitted_controller import AnswerSubmittedController
from app.controllers.form_submission_controller import FormSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
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
        # Update field names to match schema
        if 'form_answer_id' in data:
            data['form_answers_id'] = data.pop('form_answer_id')
        if 'form_submission_id' in data:
            data['form_submissions_id'] = data.pop('form_submission_id')

        required_fields = ['form_answers_id', 'form_submissions_id']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": "Missing required fields",
                "required_fields": required_fields
            }), 400

        # Validate form submission ownership
        if not user.role.is_super_user:
            form_submission = FormSubmissionController.get_form_submission(
                data['form_submissions_id']
            )
            if not form_submission or form_submission.submitted_by != user.username:
                return jsonify({"error": "Unauthorized access"}), 403

        new_answer_submitted, error = AnswerSubmittedController.create_answer_submitted(
            form_answers_id=data['form_answers_id'],
            form_submissions_id=data['form_submissions_id']
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

        # Date filters
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

        # Get answers through controller
        answers_submitted = AnswerSubmittedController.get_all_answers_submitted(user, filters)

        # Return formatted response
        response_data = {
            'total_count': len(answers_submitted),
            'filters_applied': {
                'form_id': form_id,
                'start_date': start_date,
                'end_date': end_date,
                'environment_restricted': not user.role.is_super_user
            },
            'answers_submitted': [answer.to_dict() for answer in answers_submitted]
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting answers submitted: {str(e)}")
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
        submission = FormSubmissionController.get_submission(submission_id)
        if not submission:
            return jsonify({"error": "Form submission not found"}), 404

        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
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

        # Get the submitted answer checking is_deleted=False
        answer_submitted = AnswerSubmittedController.get_answer_submitted(answer_submitted_id)
        if not answer_submitted:
            return jsonify({"error": "Submitted answer not found"}), 404

        # Access control
        if not user.role.is_super_user:
            # Site Managers and Supervisors can delete in their environment
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                if answer_submitted.form_submission.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            # Technicians can only delete their own submissions
            elif answer_submitted.form_submission.submitted_by != current_user:
                return jsonify({"error": "Cannot delete answers submitted by other users"}), 403

            # Check submission age
            submission_age = datetime.utcnow() - answer_submitted.form_submission.submitted_at
            if submission_age.days > 7:  # Configurable timeframe
                return jsonify({
                    "error": "Cannot delete answers from submissions older than 7 days"
                }), 400

        success, result = AnswerSubmittedController.delete_answer_submitted(answer_submitted_id)
        if success:
            logger.info(f"Submitted answer {answer_submitted_id} deleted by {user.username}")
            return jsonify({
                "message": "Submitted answer deleted successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error deleting submitted answer {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500