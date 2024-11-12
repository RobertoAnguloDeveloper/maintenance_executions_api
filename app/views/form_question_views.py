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
    
@form_question_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_all_form_questions():
    """Get all form questions with filtering and pagination"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Get query parameters
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        form_id = request.args.get('form_id', type=int)
        question_type_id = request.args.get('question_type_id', type=int)
        include_answers = request.args.get('include_answers', type=lambda v: v.lower() == 'true', default=False)

        # Determine environment filtering based on user role
        environment_id = None if user.role.is_super_user else user.environment_id

        # Get all form questions
        form_questions = FormQuestionController.get_all_form_questions(
            environment_id=environment_id,
            include_relations=True
        )

        if form_questions is None:
            return jsonify({"error": "Error retrieving form questions"}), 500

        # Apply additional filters
        if form_id:
            form_questions = [fq for fq in form_questions if fq.form_id == form_id]
        
        if question_type_id:
            form_questions = [fq for fq in form_questions if fq.question.question_type_id == question_type_id]

        # Calculate pagination
        total_items = len(form_questions)
        total_pages = (total_items + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Paginate results
        paginated_questions = form_questions[start_idx:end_idx]

        # Prepare response data
        response_data = {
            "metadata": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": per_page,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "filters_applied": {
                "form_id": form_id,
                "question_type_id": question_type_id,
                "environment_restricted": environment_id is not None,
                "include_answers": include_answers
            },
            "items": []
        }

        # Format question data
        for form_question in paginated_questions:
            question_data = {
                "id": form_question.id,
                "form_id": form_question.form_id,
                "form": {
                    "id": form_question.form.id,
                    "title": form_question.form.title,
                    "is_public": form_question.form.is_public
                },
                "question": {
                    "id": form_question.question.id,
                    "text": form_question.question.text,
                    "type": {
                        "id": form_question.question.question_type.id,
                        "type": form_question.question.question_type.type
                    },
                    "has_remarks": form_question.question.has_remarks
                },
                "order_number": form_question.order_number,
                "created_at": form_question.created_at.isoformat() if form_question.created_at else None,
                "updated_at": form_question.updated_at.isoformat() if form_question.updated_at else None
            }

            # Include answers if requested
            if include_answers:
                question_data["answers"] = [{
                    "id": fa.id,
                    "answer": {
                        "id": fa.answer.id,
                        "value": fa.answer.value
                    },
                    "remarks": fa.remarks
                } for fa in form_question.form_answers]

            response_data["items"].append(question_data)

        return jsonify(response_data), 200

    except ValueError as ve:
        logger.error(f"Validation error in get_all_form_questions: {str(ve)}")
        return jsonify({"error": "Invalid parameter values provided"}), 400
    except Exception as e:
        logger.error(f"Error in get_all_form_questions: {str(e)}")
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
                "has_remarks": form_question.question.has_remarks
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