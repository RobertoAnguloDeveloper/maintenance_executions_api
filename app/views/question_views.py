from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.question_controller import QuestionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

question_bp = Blueprint('questions', __name__)

@question_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.QUESTIONS)
def create_question():
    """Create a new question - Admin, Site Manager, and Supervisor"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only Admin, Site Manager, and Supervisor can create questions
        if user.role.name not in [RoleType.ADMIN, RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
            return jsonify({
                "error": "Unauthorized",
                "message": "Insufficient permissions to create questions"
            }), 403

        data = request.get_json()
        text = data.get('text')
        question_type_id = data.get('question_type_id')
        order_number = data.get('order_number')
        has_remarks = data.get('has_remarks', False)

        # Validate required fields
        if not all([text, question_type_id]):
            return jsonify({"error": "Text and question_type_id are required"}), 400

        # Validate text length
        if len(text.strip()) < 3:
            return jsonify({"error": "Question text must be at least 3 characters long"}), 400

        new_question, error = QuestionController.create_question(
            text=text,
            question_type_id=question_type_id,
            order_number=order_number,
            has_remarks=has_remarks,
            environment_id=user.environment_id  # Associate with user's environment
        )
        
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Question created successfully by user {user.username}")
        return jsonify({
            "message": "Question created successfully",
            "question": new_question.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def get_all_questions():
    """Get all questions with environment-based filtering"""
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

@question_bp.route('/type/<int:type_id>', methods=['GET'])
@jwt_required()
def get_questions_by_type(type_id):
    """Get questions by type"""
    questions = QuestionController.get_questions_by_type(type_id)
    return jsonify([q.to_dict() for q in questions]), 200

@question_bp.route('/type/<int:type_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def get_questions_by_type(type_id):
    """Get questions by type with environment-based filtering"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        if user.role.is_super_user:
            questions = QuestionController.get_questions_by_type(type_id)
        else:
            # Filter questions by type and environment
            questions = QuestionController.get_questions_by_type_and_environment(
                type_id, user.environment_id
            )

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
        allowed_fields = ['text', 'question_type_id', 'order_number', 'has_remarks']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        # Validate text if provided
        if 'text' in update_data and len(update_data['text'].strip()) < 3:
            return jsonify({"error": "Question text must be at least 3 characters long"}), 400

        updated_question, error = QuestionController.update_question(
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
    """Delete a question"""
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

        # Check if question is in use
        if QuestionController.is_question_in_use(question_id):
            return jsonify({
                "error": "Cannot delete question that is in use in forms"
            }), 400

        success, error = QuestionController.delete_question(question_id)
        if success:
            logger.info(f"Question {question_id} deleted by user {user.username}")
            return jsonify({"message": "Question deleted successfully"}), 200
        return jsonify({"error": error}), 404

    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_bp.route('/reorder', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.QUESTIONS)
def reorder_questions():
    """Reorder questions with environment-based access control"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        questions_order = data.get('questions_order', [])
        
        if not questions_order:
            return jsonify({"error": "Questions order is required"}), 400

        # Validate environment access for non-admin users
        if not user.role.is_super_user:
            # Check if all questions belong to user's environment
            for question_id, _ in questions_order:
                question = QuestionController.get_question(question_id)
                if not question or question.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access to one or more questions"}), 403

        success, error = QuestionController.reorder_questions(questions_order)
        if success:
            logger.info(f"Questions reordered by user {user.username}")
            return jsonify({"message": "Questions reordered successfully"}), 200
        return jsonify({"error": error}), 400

    except Exception as e:
        logger.error(f"Error reordering questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500