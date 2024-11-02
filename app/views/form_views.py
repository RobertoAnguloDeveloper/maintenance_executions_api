from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_controller import FormController
from app.services.auth_service import AuthService

form_bp = Blueprint('forms', __name__)

@form_bp.route('', methods=['POST'])
@jwt_required()
def create_form():
    """Create a new form with questions"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    data = request.get_json()
    required_fields = ['title', 'questions']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    new_form, error = FormController.create_form(
        title=data['title'],
        description=data.get('description'),
        user_id=user.id,
        questions=data['questions'],
        is_public=data.get('is_public', False)
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form created successfully",
        "form": new_form.to_dict()
    }), 201

@form_bp.route('/<int:form_id>/questions', methods=['POST'])
@jwt_required()
def add_questions_to_form(form_id):
    """Add new questions to an existing form"""
    data = request.get_json()
    if 'questions' not in data:
        return jsonify({"error": "Questions are required"}), 400

    updated_form, error = FormController.add_questions_to_form(
        form_id=form_id,
        questions=data['questions']
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Questions added successfully",
        "form": updated_form.to_dict()
    }), 200

@form_bp.route('/<int:form_id>/questions/reorder', methods=['PUT'])
@jwt_required()
def reorder_form_questions(form_id):
    """Reorder questions in a form"""
    data = request.get_json()
    if 'question_order' not in data:
        return jsonify({"error": "Question order is required"}), 400

    updated_form, error = FormController.reorder_questions(
        form_id=form_id,
        question_order=data['question_order']
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Questions reordered successfully",
        "form": updated_form.to_dict()
    }), 200

@form_bp.route('/<int:form_id>/submit', methods=['POST'])
@jwt_required()
def submit_form(form_id):
    """Submit a form with answers"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    if 'answers' not in data:
        return jsonify({"error": "Answers are required"}), 400

    submission, error = FormController.submit_form(
        form_id=form_id,
        username=current_user,
        answers=data['answers'],
        attachments=data.get('attachments')
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form submitted successfully",
        "submission": submission.to_dict()
    }), 201

@form_bp.route('/<int:form_id>/submissions', methods=['GET'])
@jwt_required()
def get_form_submissions(form_id):
    """Get all submissions for a specific form"""
    submissions = FormController.get_form_submissions(form_id)
    return jsonify([submission.to_dict() for submission in submissions]), 200

@form_bp.route('/<int:form_id>/statistics', methods=['GET'])
@jwt_required()
def get_form_statistics(form_id):
    """Get statistics for a specific form"""
    stats = FormController.get_form_statistics(form_id)
    return jsonify(stats), 200