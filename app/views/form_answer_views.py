# app/views/form_answer_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_answer_controller import FormAnswerController
from app.controllers.form_question_controller import FormQuestionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

form_answer_bp = Blueprint('form-answers', __name__)

@form_answer_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_form_answer():
    """Create a new form answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        required_fields = ['form_question_id', 'answer_id']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate access to form question
        if not user.role.is_super_user:
            form_question = FormQuestionController.get_form_question(data['form_question_id'])
            if not form_question or form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        new_form_answer, error = FormAnswerController.create_form_answer(
            form_question_id=data['form_question_id'],
            answer_id=data['answer_id'],
            remarks=data.get('remarks')
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Form answer created by user {user.username}")
        return jsonify({
            "message": "Form answer created successfully",
            "form_answer": new_form_answer.to_dict()
        }), 201

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
                
        # Use RoleType constants instead of Role enum
        if user.role.name == RoleType.TECHNICIAN:
            # Technicians can only see public forms
            return None
        elif user.role.name in [RoleType.SUPERVISOR, RoleType.SITE_MANAGER]:
            # Supervisors and Site Managers see forms in their environment
            return None
        else:
            # Admins see all forms
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
    """Update a form answer"""
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
        update_data = {k: v for k, v in data.items() if k in ['answer_id', 'remarks']}

        updated_form_answer, error = FormAnswerController.update_form_answer(
            form_answer_id,
            **update_data
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Form answer {form_answer_id} updated by user {user.username}")
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

        form_answer = FormAnswerController.get_form_answer(form_answer_id)
        if not form_answer:
            return jsonify({"error": "Form answer not found"}), 404

        # Check access
        if not user.role.is_super_user:
            if form_answer.form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        # Check if answer is submitted
        if FormAnswerController.is_answer_submitted(form_answer_id):
            return jsonify({"error": "Cannot delete submitted answer"}), 400

        success, error = FormAnswerController.delete_form_answer(form_answer_id)
        if success:
            logger.info(f"Form answer {form_answer_id} deleted by user {user.username}")
            return jsonify({"message": "Form answer deleted successfully"}), 200
        return jsonify({"error": error}), 404

    except Exception as e:
        logger.error(f"Error deleting form answer {form_answer_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500