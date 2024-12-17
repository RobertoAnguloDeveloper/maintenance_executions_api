from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_submission_controller import FormSubmissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

form_submission_bp = Blueprint('form_submissions', __name__)

@form_submission_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_submission():
    """Create a new form submission"""
    try:
        current_user = get_jwt_identity()

        # Handle multipart/form-data for signatures
        data = request.form.to_dict() if request.form else request.get_json()
        files = request.files.to_dict()

        if not data or 'form_id' not in data:
            return jsonify({"error": "form_id is required"}), 400

        # Process answers data
        answers_data = data.get('answers', [])
        for answer in answers_data:
            if answer.get('is_signature'):
                file_key = f"signature_{answer.get('question_id')}"
                if file_key in files:
                    answer['signature_file'] = files[file_key]

        submission, error = FormSubmissionController.create_submission(
            form_id=int(data['form_id']),
            username=current_user,
            answers_data=answers_data
        )

        if error:
            return jsonify({"error": error}), 400

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
def get_all_submissions():
    """Get all submissions with filtering"""
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
        end_date = request.args.get('end_date')
        if start_date and end_date:
            filters['date_range'] = {
                'start': start_date,
                'end': end_date
            }

        submissions = FormSubmissionController.get_all_submissions(user, filters)

        return jsonify({
            'total_count': len(submissions),
            'filters_applied': filters,
            'submissions': [sub.to_dict() for sub in submissions]
        }), 200

    except Exception as e:
        logger.error(f"Error getting submissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submission(submission_id):
    """Get a specific submission with its answers"""
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

        # Get answers with access control
        answers, error = FormSubmissionController.get_submission_answers(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 403

        submission_data = submission.to_dict()
        submission_data['answers'] = answers

        return jsonify(submission_data), 200

    except Exception as e:
        logger.error(f"Error getting submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_submission_bp.route('/my-submissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view_own_submissions", entity_type=EntityType.SUBMISSIONS)
def get_my_submissions():
    """Get all submissions for the current user with filtering"""
    try:
        current_user = get_jwt_identity()
        
        # Get filter parameters
        filters = {}
        
        # Date range filters
        start_date = request.args.get('start_date')
        if start_date:
            filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
            
        end_date = request.args.get('end_date')
        if end_date:
            filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')
            
        # Form filter
        form_id = request.args.get('form_id', type=int)
        if form_id:
            filters['form_id'] = form_id

        submissions, error = FormSubmissionController.get_user_submissions(
            username=current_user,
            filters=filters
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "total_count": len(submissions),
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "form_id": form_id
            },
            "submissions": [sub.to_dict() for sub in submissions]
        }), 200

    except Exception as e:
        logger.error(f"Error getting user submissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_submission(submission_id):
    """Delete a submission with cascade soft delete"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        success, message = FormSubmissionController.delete_submission(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": "Submission deleted successfully",
            "submission_id": submission_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>/answers', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submission_answers(submission_id):
    """Get all answers for a specific submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answers, error = FormSubmissionController.get_submission_answers(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            'submission_id': submission_id,
            'total_answers': len(answers),
            'answers': answers
        }), 200

    except Exception as e:
        logger.error(f"Error getting submission answers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500