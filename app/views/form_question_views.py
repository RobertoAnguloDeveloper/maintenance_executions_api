# app/views/form_question_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_controller import FormController
from app.controllers.form_question_controller import FormQuestionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

form_question_bp = Blueprint('form_questions', __name__)

@form_question_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_form_question():
    """Create a new form question mapping"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        required_fields = ['form_id', 'question_id', 'order_number']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Check form access
        if not user.role.is_super_user:
            form = FormController.get_form(data['form_id'])
            if not form or form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access to form"}), 403

        new_form_question, error = FormQuestionController.create_form_question(
            form_id=data['form_id'],
            question_id=data['question_id'],
            order_number=data['order_number']
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Form question created by user {user.username}")
        return jsonify({
            "message": "Form question created successfully",
            "form_question": new_form_question.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating form question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_question_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_form_questions(form_id):
    """Get all questions for a specific form"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Check form access
        if not user.role.is_super_user:
            form = FormController.get_form(form_id)
            if not form or form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access to form"}), 403

        form_questions = FormQuestionController.get_questions_by_form(form_id)
        return jsonify([fq.to_dict() for fq in form_questions]), 200

    except Exception as e:
        logger.error(f"Error getting form questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_question_bp.route('/<int:form_question_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS)
def update_form_question(form_question_id):
    """Update a form question mapping"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        form_question = FormQuestionController.get_form_question(form_question_id)
        if not form_question:
            return jsonify({"error": "Form question not found"}), 404

        # Check form access
        if not user.role.is_super_user:
            if form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        update_data = {
            k: v for k, v in data.items() 
            if k in ['question_id', 'order_number']
        }

        updated_form_question, error = FormQuestionController.update_form_question(
            form_question_id,
            **update_data
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Form question {form_question_id} updated by user {user.username}")
        return jsonify({
            "message": "Form question updated successfully",
            "form_question": updated_form_question.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating form question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_question_bp.route('/<int:form_question_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.FORMS)
def delete_form_question(form_question_id):
    """Delete a form question mapping"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        form_question = FormQuestionController.get_form_question(form_question_id)
        if not form_question:
            return jsonify({"error": "Form question not found"}), 404

        # Check form access
        if not user.role.is_super_user:
            if form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        success, error = FormQuestionController.delete_form_question(form_question_id)
        if success:
            logger.info(f"Form question {form_question_id} deleted by user {user.username}")
            return jsonify({"message": "Form question deleted successfully"}), 200
        return jsonify({"error": error}), 404

    except Exception as e:
        logger.error(f"Error deleting form question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_question_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def bulk_create_form_questions():
    """Bulk create form questions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if 'form_id' not in data or 'questions' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        # Check form access
        if not user.role.is_super_user:
            form = FormController.get_form(data['form_id'])
            if not form or form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access to form"}), 403

        form_questions, error = FormQuestionController.bulk_create_form_questions(
            form_id=data['form_id'],
            questions=data['questions']
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Bulk form questions created by user {user.username}")
        return jsonify({
            "message": "Form questions created successfully",
            "form_questions": [fq.to_dict() for fq in form_questions]
        }), 201

    except Exception as e:
        logger.error(f"Error bulk creating form questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500