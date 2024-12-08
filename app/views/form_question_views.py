# app/views/form_question_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_controller import FormController
from app.controllers.form_question_controller import FormQuestionController
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

form_question_bp = Blueprint('form-questions', __name__)

@form_question_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_form_question():
    """Create a new form question mapping"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        required_fields = ['form_id', 'question_id']
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
            order_number=data.get('order_number')
        )

        if error:
            return jsonify({"error": error}), 400

        # Create serializable response
        response_data = {
            "message": "Form question created successfully",
            "form_question": {
                "id": new_form_question.id,
                "form_id": new_form_question.form_id,
                "question_id": new_form_question.question_id,
                "order_number": new_form_question.order_number,
                "question": {
                    "id": new_form_question.question.id,
                    "text": new_form_question.question.text,
                    "type": new_form_question.question.question_type.type if new_form_question.question.question_type else None,
                    "remarks": new_form_question.question.remarks
                },
                "created_at": new_form_question.created_at.isoformat() if new_form_question.created_at else None,
                "updated_at": new_form_question.updated_at.isoformat() if new_form_question.updated_at else None
            }
        }

        logger.info(f"Form question created by user {user.username}")
        return jsonify(response_data), 201

    except Exception as e:
        logger.error(f"Error creating form question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_question_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_all_form_questions():
    """Get all form questions with filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        form_id = request.args.get('form_id', type=int)
        
        # Get all form questions
        questions = FormQuestionController.get_all_form_questions(
            include_relations=True
        )

        # Apply form_id filter if provided
        if form_id:
            questions = [q for q in questions if q.get('form_id') == form_id]

        # Calculate pagination
        total_items = len(questions)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Ensure we don't exceed list bounds
        start_idx = min(start_idx, total_items)
        end_idx = min(end_idx, total_items)
        
        paginated_questions = questions[start_idx:end_idx]

        return jsonify({
            "metadata": {
                "total_items": total_items,
                "current_page": page,
                "per_page": per_page,
            },
            "items": paginated_questions
        }), 200

    except Exception as e:
        logger.error(f"Error getting form questions: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

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

        questions = FormQuestionController.get_questions_by_form(form_id)
        
        return jsonify({
            "total_questions": len(questions),
            "questions": questions
        }), 200

    except Exception as e:
        logger.error(f"Error getting form questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_question_bp.route('/<int:form_question_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_form_question(form_question_id: int):
    """Get a specific form question with all related data"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get the form question with relationships
        form_question = FormQuestionController.get_form_question_detail(form_question_id)
        
        if not form_question:
            return jsonify({"error": "Form question not found"}), 404

        # Check environment access for non-admin users
        if not user.role.is_super_user:
            if form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        # Build response data
        response_data = {
            "id": form_question.id,
            "form": {
                "id": form_question.form.id,
                "title": form_question.form.title,
                "description": form_question.form.description,
                "is_public": form_question.form.is_public,
                "creator": {
                    "id": form_question.form.creator.id,
                    "username": form_question.form.creator.username,
                    "environment_id": form_question.form.creator.environment_id
                }
            },
            "question": {
                "id": form_question.question.id,
                "text": form_question.question.text,
                "type": {
                    "id": form_question.question.question_type.id,
                    "type": form_question.question.question_type.type
                },
                "remarks": form_question.question.remarks
            },
            "order_number": form_question.order_number,
            "answers": [{
                "id": form_answer.id,
                "answer": {
                    "id": form_answer.answer.id,
                    "value": form_answer.answer.value
                },
                "remarks": form_answer.remarks
            } for form_answer in form_question.form_answers],
            "metadata": {
                "created_at": form_question.created_at.isoformat() if form_question.created_at else None,
                "updated_at": form_question.updated_at.isoformat() if form_question.updated_at else None
            }
        }

        return jsonify(response_data), 200

    except ValueError as ve:
        logger.error(f"Validation error in get_form_question: {str(ve)}")
        return jsonify({"error": "Invalid form question ID"}), 400
    except Exception as e:
        logger.error(f"Error getting form question {form_question_id}: {str(e)}")
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
    """Delete a form question with cascade soft delete"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get form question with is_deleted=False check
        form_question = FormQuestionController.get_form_question(form_question_id)
        if not form_question:
            return jsonify({"error": "Form question not found"}), 404

        # Access control
        if not user.role.is_super_user:
            if form_question.form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        # Check if there are any submissions using this question
        has_submissions = (AnswerSubmitted.query
            .join(FormAnswer)
            .filter(
                FormAnswer.form_question_id == form_question_id,
                AnswerSubmitted.is_deleted == False
            ).first() is not None)

        if has_submissions and user.role.name not in [RoleType.ADMIN, RoleType.SITE_MANAGER]:
            return jsonify({
                "error": "Cannot delete question with existing submissions"
            }), 400

        success, result = FormQuestionController.delete_form_question(form_question_id)
        if success:
            logger.info(f"Form question {form_question_id} and associated data deleted by {user.username}")
            return jsonify({
                "message": "Form question and associated data deleted successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

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
        if not data or 'form_id' not in data or 'questions' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        # Validate questions data structure
        if not isinstance(data['questions'], list):
            return jsonify({"error": "Questions must be provided as a list"}), 400

        if not data['questions']:
            return jsonify({"error": "At least one question is required"}), 400

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
        
        # Serialize the response
        response_data = {
            "message": "Form questions created successfully",
            "form_questions": [{
                "id": fq.id,
                "form_id": fq.form_id,
                "question_id": fq.question_id,
                "order_number": fq.order_number,
                "question": {
                    "id": fq.question.id,
                    "text": fq.question.text,
                    "type": fq.question.question_type.type if fq.question.question_type else None
                } if fq.question else None,
                "created_at": fq.created_at.isoformat() if fq.created_at else None,
                "updated_at": fq.updated_at.isoformat() if fq.updated_at else None
            } for fq in form_questions]
        }

        return jsonify(response_data), 201

    except Exception as e:
        logger.error(f"Error bulk creating form questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500