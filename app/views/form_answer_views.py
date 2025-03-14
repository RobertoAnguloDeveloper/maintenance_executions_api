# app/views/form_answer_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_answer_controller import FormAnswerController
from app.controllers.form_question_controller import FormQuestionController
from app.models.answer import Answer
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

form_answer_bp = Blueprint('form-answers', __name__)

@form_answer_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_form_answer():
    """Create a new form answer mapping for possible answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        required_fields = ['form_question_id', 'answer_id']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate access to form question
        form_question = FormQuestion.query.get(data['form_question_id'])
        if not form_question:
            return jsonify({"error": "Form question not found"}), 404

        # Check authorization
        if not user.role.is_super_user:
            if form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        # Verify answer exists
        answer = Answer.query.get(data['answer_id'])
        if not answer:
            return jsonify({"error": "Answer not found"}), 404

        # Check if this answer is already mapped to this question
        existing_form_answer = FormAnswer.query.filter_by(
            form_question_id=data['form_question_id'],
            answer_id=data['answer_id']
        ).first()
        
        if existing_form_answer:
            return jsonify({"error": "This answer is already mapped to this question"}), 400

        new_form_answer, error = FormAnswerController.create_form_answer(
            form_question_id=data['form_question_id'],
            answer_id=data['answer_id']
        )

        if error:
            return jsonify({"error": error}), 400

        # Create serializable response
        response_data = {
            "message": "Form answer option created successfully",
            "form_answer": {
                "id": new_form_answer.id,
                "form_question": {
                    "id": new_form_answer.form_question_id,
                    "form": new_form_answer.form_question.form.title,
                    "question": new_form_answer.form_question.question.text,
                    "type": new_form_answer.form_question.question.question_type.type
                },
                "answer": {
                    "id": new_form_answer.answer.id,
                    "value": new_form_answer.answer.value
                },
                "created_at": new_form_answer.created_at.isoformat() if new_form_answer.created_at else None,
                "updated_at": new_form_answer.updated_at.isoformat() if new_form_answer.updated_at else None
            }
        }

        logger.info(f"Form answer option created by user {user.username}")
        return jsonify(response_data), 201

    except Exception as e:
        logger.error(f"Error creating form answer: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_answer_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def bulk_create_form_answers():
    """Bulk create form answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if 'form_answers' not in data:
            return jsonify({"error": "Form answers are required"}), 400

        # Validate all form questions access
        if not user.role.is_super_user:
            form_question_ids = [fa['form_question_id'] for fa in data['form_answers']]
            for fq_id in form_question_ids:
                form_question = FormQuestionController.get_form_question(fq_id)
                if not form_question or form_question.form.creator.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403

        form_answers, error = FormAnswerController.bulk_create_form_answers(data['form_answers'])
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Bulk form answers created by user {user.username}")
        return jsonify({
            "message": "Form answers created successfully",
            "form_answers": [fa.to_dict() for fa in form_answers]
        }), 201

    except Exception as e:
        logger.error(f"Error creating bulk form answers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_answer_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_all_form_answers():
    """Get all form answers with role-based filtering"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
                
        form_answers = FormAnswerController.get_all_form_answers()
        
        return jsonify([form_answers.to_dict() for form_answers in form_answers]), 200
        
    except Exception as e:
        logger.error(f"Error getting forms: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_answer_bp.route('/question/<int:form_question_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_answers_by_question(form_question_id):
    """Get all answers for a specific form question"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Validate access to form question
        if not user.role.is_super_user:
            form_question = FormQuestionController.get_form_question(form_question_id)
            if not form_question or form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        form_answers = FormAnswerController.get_answers_by_question(form_question_id)
        return jsonify([fa.to_dict() for fa in form_answers]), 200

    except Exception as e:
        logger.error(f"Error getting form answers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_answer_bp.route('/<int:form_answer_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_form_answer(form_answer_id):
    """Get a specific form answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        form_answer = FormAnswerController.get_form_answer(form_answer_id)
        if not form_answer:
            return jsonify({"error": "Form answer not found"}), 404

        # Check access
        if not user.role.is_super_user:
            if form_answer.form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(form_answer.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting form answer {form_answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_answer_bp.route('/<int:form_answer_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS)
def update_form_answer(form_answer_id):
    """Update a form answer mapping"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        form_answer = FormAnswerController.get_form_answer(form_answer_id)
        if not form_answer:
            return jsonify({"error": "Form answer not found"}), 404

        # Check access
        if not user.role.is_super_user:
            if form_answer.form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        update_data = {k: v for k, v in data.items() 
                      if k in ['answer_id', 'form_question_id']}

        updated_form_answer, error = FormAnswerController.update_form_answer(
            form_answer_id,
            current_user=user,  # Pass the user object
            **update_data
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Form answer updated successfully",
            "form_answer": updated_form_answer.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating form answer {form_answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_answer_bp.route('/<int:form_answer_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.FORMS)
def delete_form_answer(form_answer_id):
    """Delete a form answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get form answer checking is_deleted=False
        form_answer = FormAnswerController.get_form_answer(form_answer_id)
        if not form_answer:
            return jsonify({"error": "Form answer not found"}), 404

        # Access control
        if not user.role.is_super_user:
            if form_answer.form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        success, result = FormAnswerController.delete_form_answer(form_answer_id)
        if success:
            logger.info(f"Form answer {form_answer_id} deleted by {user.username}")
            return jsonify({
                "message": "Form answer deleted successfully",
                "deleted_item": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error deleting form answer {form_answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500