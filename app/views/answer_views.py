# app/views/answer_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.answer_controller import AnswerController
from app.controllers.form_controller import FormController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

answer_bp = Blueprint('answers', __name__)

@answer_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.ANSWERS)
def create_answer():
    """Create a new answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        value = data.get('value')
        remarks = data.get('remarks')

        if not value:
            return jsonify({"error": "Value is required"}), 400

        # Validate value length
        if len(str(value).strip()) < 1:
            return jsonify({"error": "Answer value cannot be empty"}), 400

        new_answer, error = AnswerController.create_answer(
            value=value,
            remarks=remarks
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Answer created by user {user.username}")
        return jsonify({
            "message": "Answer created successfully",
            "answer": new_answer.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating answer: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.ANSWERS)
def bulk_create_answers():
    """Create multiple answers at once"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        answers_data = data.get('answers', [])

        if not answers_data:
            return jsonify({"error": "No answers provided"}), 400

        # Validate all answers
        for answer in answers_data:
            if not answer.get('value'):
                return jsonify({"error": "Value is required for all answers"}), 400
            if len(str(answer['value']).strip()) < 1:
                return jsonify({"error": "Answer values cannot be empty"}), 400

        # Add environment ID to each answer
        for answer in answers_data:
            answer['environment_id'] = user.environment_id

        new_answers, error = AnswerController.bulk_create_answers(answers_data)

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Bulk answers created by user {user.username}")
        return jsonify({
            "message": f"{len(new_answers)} answers created successfully",
            "answers": [answer.to_dict() for answer in new_answers]
        }), 201

    except Exception as e:
        logger.error(f"Error creating bulk answers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ANSWERS)
def get_all_answers():
    """Get all answers with environment-based filtering"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        if user.role.is_super_user:
            answers = AnswerController.get_all_answers()
        else:
            # Filter answers by environment
            answers = AnswerController.get_answers_by_environment(user.environment_id)

        return jsonify([answer.to_dict() for answer in answers]), 200

    except Exception as e:
        logger.error(f"Error getting answers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_bp.route('/<int:answer_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ANSWERS)
def get_answer(answer_id):
    """Get a specific answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answer = AnswerController.get_answer(answer_id)
        if not answer:
            return jsonify({"error": "Answer not found"}), 404

        # Check environment access for non-admin users
        if not user.role.is_super_user and answer.environment_id != user.environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(answer.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting answer {answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ANSWERS)
def get_answers_by_form(form_id):
    """Get answers for a specific form"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Check form access
        if not user.role.is_super_user:
            form = FormController.get_form(form_id)
            if not form or form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access to form"}), 403

        answers = AnswerController.get_answers_by_form(form_id)
        return jsonify([answer.to_dict() for answer in answers]), 200

    except Exception as e:
        logger.error(f"Error getting answers for form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_bp.route('/<int:answer_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.ANSWERS)
def update_answer(answer_id):
    """Update an answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the answer
        answer = AnswerController.get_answer(answer_id)
        if not answer:
            return jsonify({"error": "Answer not found"}), 404

        # Check environment access for non-admin users
        if not user.role.is_super_user and answer.environment_id != user.environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        
        # Validate value if provided
        if 'value' in data:
            if not data['value'] or len(str(data['value']).strip()) < 1:
                return jsonify({"error": "Answer value cannot be empty"}), 400

        updated_answer, error = AnswerController.update_answer(
            answer_id,
            value=data.get('value'),
            remarks=data.get('remarks')
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Answer {answer_id} updated by user {user.username}")
        return jsonify({
            "message": "Answer updated successfully",
            "answer": updated_answer.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating answer {answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_bp.route('/<int:answer_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.ANSWERS)
def delete_answer(answer_id):
    """Delete an answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the answer
        answer = AnswerController.get_answer(answer_id)
        if not answer:
            return jsonify({"error": "Answer not found"}), 404

        # Check environment access for non-admin users
        if not user.role.is_super_user and answer.environment_id != user.environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        success, error = AnswerController.delete_answer(answer_id)
        if success:
            logger.info(f"Answer {answer_id} deleted by user {user.username}")
            return jsonify({"message": "Answer deleted successfully"}), 200
        return jsonify({"error": error}), 404

    except Exception as e:
        logger.error(f"Error deleting answer {answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500