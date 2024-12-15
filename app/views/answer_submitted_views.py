from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.answer_submitted_controller import AnswerSubmittedController
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

        # Handle multipart/form-data for potential signatures
        data = request.form.to_dict() if request.form else request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['form_submission_id', 'question_text', 'answer_text']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": "Missing required fields",
                "required_fields": required_fields
            }), 400

        # Handle signature if present
        is_signature = data.get('is_signature', False)
        signature_file = request.files.get('signature') if is_signature else None

        # Validate signature file if required
        if is_signature and not signature_file:
            return jsonify({"error": "Signature file is required for signature questions"}), 400

        answer_submitted, error = AnswerSubmittedController.create_answer_submitted(
            form_submission_id=int(data['form_submission_id']),
            question_text=data['question_text'],
            answer_text=data['answer_text'],
            is_signature=is_signature,
            signature_file=signature_file,
            current_user=current_user
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

@answer_submitted_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def bulk_create_answers_submitted():
    """Bulk create submitted answers"""
    try:
        current_user = get_jwt_identity()
        
        # Handle multipart/form-data for signatures
        data = request.form.to_dict() if request.form else request.get_json()
        files = request.files.to_dict()
        
        if not data or 'form_submission_id' not in data or 'submissions' not in data:
            return jsonify({
                "error": "Missing required fields: form_submission_id and submissions"
            }), 400

        # Process submissions data and handle signatures
        submissions_data = []
        for submission in data['submissions']:
            submission_data = {
                'question_text': submission['question_text'],
                'answer_text': submission['answer_text'],
                'is_signature': submission.get('is_signature', False)
            }
            
            # Add signature file if present
            if submission_data['is_signature']:
                file_key = f"signature_{submission.get('question_id')}"
                if file_key in files:
                    submission_data['signature_file'] = files[file_key]
                else:
                    return jsonify({
                        "error": f"Missing signature file for question {submission.get('question_id')}"
                    }), 400
                    
            submissions_data.append(submission_data)
            
        submissions, error = AnswerSubmittedController.bulk_create_answers_submitted(
            form_submission_id=int(data['form_submission_id']),
            submissions_data=submissions_data,
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({
            "message": "Answers submitted successfully",
            "submissions": submissions
        }), 201
        
    except Exception as e:
        logger.error(f"Error in bulk create answers submitted: {str(e)}")
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
        
        # Form submission filter
        form_submission_id = request.args.get('form_submission_id', type=int)
        if form_submission_id:
            filters['form_submission_id'] = form_submission_id

        # Date range filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            filters['date_range'] = {
                'start': start_date,
                'end': end_date
            }

        answers = AnswerSubmittedController.get_all_answers_submitted(user, filters)

        return jsonify({
            'total_count': len(answers),
            'filters_applied': filters,
            'answers': answers
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

        answer_submitted, error = AnswerSubmittedController.get_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 404

        return jsonify(answer_submitted), 200

    except Exception as e:
        logger.error(f"Error getting answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/submission/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_answers_by_submission(submission_id):
    """Get all submitted answers for a form submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answers, error = AnswerSubmittedController.get_answers_by_submission(
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
        logger.error(f"Error getting answers for submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.SUBMISSIONS)
def update_answer_submitted(answer_submitted_id):
    """Update a submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        updated_answer, error = AnswerSubmittedController.update_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            answer_text=data.get('answer_text'),
            current_user=current_user,
            user_role=user.role.name
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

        success, message = AnswerSubmittedController.delete_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message,
            "deleted_id": answer_submitted_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500