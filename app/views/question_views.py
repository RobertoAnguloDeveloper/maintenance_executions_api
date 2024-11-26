# app/views/question_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.question_controller import QuestionController
from app.controllers.question_type_controller import QuestionTypeController
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

question_bp = Blueprint('questions', __name__)

@question_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.QUESTIONS)
def create_question():
    """Create a new question"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        text = data.get('text')
        question_type_id = data.get('question_type_id')
        remarks = data.get('remarks')

        # Validate required fields
        if not all([text, question_type_id]):
            return jsonify({"error": "Text and question_type_id are required"}), 400

        # Validate text length
        if len(text.strip()) < 3:
            return jsonify({"error": "Question text must be at least 3 characters long"}), 400

        new_question, error = QuestionController.create_question(
            text=text,
            question_type_id=question_type_id,
            remarks=remarks
        )
        
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Question created by user {user.username}")
        return jsonify({
            "message": "Question created successfully",
            "question": new_question.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@question_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.QUESTIONS)
def bulk_create_questions():
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if not data or 'questions' not in data:
            return jsonify({"error": "Questions data is required"}), 400

        questions_data = data['questions']
        if not isinstance(questions_data, list) or not questions_data:
            return jsonify({"error": "At least one question is required"}), 400

        if not user.role.is_super_user:
            for question in questions_data:
                question_type = QuestionTypeController.get_question_type(
                    question.get('question_type_id')
                )
                if not question_type or question_type.environment_id != user.environment_id:
                    return jsonify({
                        "error": "Unauthorized access to one or more question types"
                    }), 403

        new_questions, error = QuestionController.bulk_create_questions(questions_data)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Bulk questions created by user {user.username}")
        return jsonify({
            "message": f"{len(new_questions)} questions created successfully",
            "questions": [question.to_dict() for question in new_questions]
        }), 201

    except Exception as e:
        logger.error(f"Error creating bulk questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def get_all_questions():
    """Get all questions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        if user.role.is_super_user:
            questions = QuestionController.get_all_questions()
        else:
            # Filter questions by environment
            questions = QuestionController.get_questions_by_environment(user.environment_id)

        return jsonify([q.to_dict() for q in questions]), 200

    except Exception as e:
        logger.error(f"Error getting questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('/by-type/<int:type_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def get_questions_by_type_id(type_id):
    """Get questions by type"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        if user.role.is_super_user:
            questions = QuestionController.get_questions_by_type(type_id)

        return jsonify([q.to_dict() for q in questions]), 200

    except Exception as e:
        logger.error(f"Error getting questions by type: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('/<int:question_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def get_question(question_id):
    """Get a specific question"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        question = QuestionController.get_question(question_id)
        if not question:
            return jsonify({"error": "Question not found"}), 404

        # Check environment access for non-admin users
        if not user.role.is_super_user and question.environment_id != user.environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(question.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting question {question_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
#View
@question_bp.route('/search', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def search_questions():
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        search_query = request.args.get('text')  # Changed from 'q' to 'text'
        remarks = request.args.get('remarks')
        question_type_id = request.args.get('type_id', type=int)
        environment_id = None if user.role.is_super_user else user.environment_id

        questions = QuestionController.search_questions(
            search_query=search_query,
            remarks=remarks,
            environment_id=environment_id
        )

        return jsonify({
            "total_results": len(questions),
            "search_criteria": {
                "query": search_query,
                "remarks": remarks,
                "question_type_id": question_type_id,
                "environment_restricted": environment_id is not None
            },
            "results": [q.to_dict() for q in questions]
        }), 200

    except Exception as e:
        logger.error(f"Error searching questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('/<int:question_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.QUESTIONS)
def update_question(question_id):
    """Update a question"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the question
        question = QuestionController.get_question(question_id)
        if not question:
            return jsonify({"error": "Question not found"}), 404

        # Check environment access for non-admin users
        if not user.role.is_super_user and question.environment_id != user.environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        allowed_fields = ['text', 'question_type_id', 'remarks']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        # Validate text if provided
        if 'text' in update_data and len(update_data['text'].strip()) < 3:
            return jsonify({"error": "Question text must be at least 3 characters long"}), 400

        updated_question, error = QuestionController.update_question(
            user,
            question_id,
            **update_data
        )
        
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Question {question_id} updated by user {user.username}")
        return jsonify({
            "message": "Question updated successfully",
            "question": updated_question.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating question {question_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('/<int:question_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.QUESTIONS)
def delete_question(question_id):
    """Delete a question with cascade soft delete"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the question with is_deleted=False check
        question = QuestionController.get_question(question_id)
        if not question:
            return jsonify({"error": "Question not found"}), 404

        # Check if question is in use in any non-deleted form
        active_forms = (FormQuestion.query
            .join(Form)
            .filter(
                FormQuestion.question_id == question_id,
                FormQuestion.is_deleted == False,
                Form.is_deleted == False
            ).count())
            
        if active_forms > 0:
            return jsonify({
                "error": "Cannot delete question that is in use in active forms",
                "active_forms": active_forms
            }), 400

        success, result = QuestionController.delete_question(question_id)
        if success:
            logger.info(f"Question {question_id} and associated data deleted by {user.username}")
            return jsonify({
                "message": "Question and associated data deleted successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500