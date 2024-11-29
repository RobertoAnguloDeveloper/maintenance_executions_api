from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.question_type_controller import QuestionTypeController
from app.models.question import Question
from app.services.auth_service import AuthService
from app.services.question_type_service import QuestionTypeService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

question_type_bp = Blueprint('question_types', __name__)

@question_type_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.QUESTION_TYPES)
def create_question_type():
    """Create a new question type - Admin and Site Manager only"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only Admin and Site Manager can create question types
        if user.role.name not in [RoleType.ADMIN]:
            return jsonify({
                "error": "Unauthorized",
                "message": "Only administrators and site managers can create question types"
            }), 403

        data = request.get_json()
        if not data or 'type' not in data:
            return jsonify({"error": "Type is required"}), 400

        # Validate type format
        type_name = data['type'].strip()
        if not type_name or ' ' in type_name:
            return jsonify({
                "error": "Type must be a non-empty string without spaces"
            }), 400

        question_type, error = QuestionTypeService.create_question_type(type_name)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Question type '{type_name}' created by user {user.username}")
        return jsonify({
            "message": "Question type created successfully",
            "question_type": question_type.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating question type: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_type_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTION_TYPES)
def get_all_question_types():
    """Get all non-deleted question types"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        question_types = QuestionTypeController.get_all_question_types()
        
        return jsonify([qt.to_dict() for qt in question_types]), 200

    except Exception as e:
        logger.error(f"Error getting question types: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_type_bp.route('/<int:type_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTION_TYPES)
def get_question_type(type_id):
    """Get a specific question type - Available to all authenticated users"""
    try:
        question_type = QuestionTypeService.get_question_type(type_id)
        if not question_type:
            return jsonify({"error": "Question type not found"}), 404
            
        return jsonify(question_type.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting question type {type_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_type_bp.route('/<int:type_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.QUESTION_TYPES)
def update_question_type(type_id):
    """Update a question type - Admin and Site Manager only"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only Admin and Site Manager can update question types
        if user.role.name not in [RoleType.ADMIN, RoleType.SITE_MANAGER]:
            return jsonify({
                "error": "Unauthorized",
                "message": "Only administrators and site managers can update question types"
            }), 403

        data = request.get_json()
        if not data or 'type' not in data:
            return jsonify({"error": "Type is required"}), 400

        # Validate type format
        type_name = data['type'].strip()
        if not type_name or ' ' in type_name:
            return jsonify({
                "error": "Type must be a non-empty string without spaces"
            }), 400

        # Check if it's a core question type
        question_type = QuestionTypeService.get_question_type(type_id)
        if question_type and question_type.type in ['single_text', 'multiple_choice', 'single_choice', 'date']:
            return jsonify({"error": "Cannot modify core question types"}), 403

        updated_type, error = QuestionTypeService.update_question_type(type_id, type_name)
        if error:
            if error == "Question type not found":
                return jsonify({"error": error}), 404
            return jsonify({"error": error}), 400

        logger.info(f"Question type {type_id} updated to '{type_name}' by user {user.username}")
        return jsonify({
            "message": "Question type updated successfully",
            "question_type": updated_type.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating question type {type_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@question_type_bp.route('/<int:type_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.QUESTION_TYPES)
def delete_question_type(type_id):
    """Delete a question type with cascade validation - Admin only"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only Admin can delete question types
        if user.role.name != RoleType.ADMIN:
            return jsonify({
                "error": "Unauthorized",
                "message": "Only administrators can delete question types"
            }), 403

        # Get the question type checking is_deleted=False
        question_type = QuestionTypeService.get_question_type(type_id)
        if not question_type:
            return jsonify({"error": "Question type not found"}), 404

        # Check if it's a core question type
        if question_type.type in ['single_text', 'multiple_choice', 'single_choice', 'date']:
            return jsonify({"error": "Cannot delete core question types"}), 403

        # Check for active questions using this type
        active_questions = Question.query.filter_by(
            question_type_id=type_id,
            is_deleted=False
        ).count()
        
        if active_questions > 0:
            return jsonify({
                "error": f"Cannot delete question type with {active_questions} active questions",
                "active_questions": active_questions
            }), 400

        success, result = QuestionTypeService.delete_question_type(type_id)
        if success:
            logger.info(f"Question type {type_id} deleted by {user.username}")
            return jsonify({
                "message": "Question type deleted successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error deleting question type {type_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500