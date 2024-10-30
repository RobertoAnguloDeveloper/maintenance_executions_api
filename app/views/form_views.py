from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_controller import FormController
from app.services.auth_service import AuthService

form_bp = Blueprint('forms', __name__)

@form_bp.route('', methods=['POST'])
@jwt_required()
def create_form():
    """Create a new form"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    question_id = data.get('question_id')
    answer_id = data.get('answer_id')
    is_public = data.get('is_public', False)

    if not all([title, question_id, answer_id]):
        return jsonify({"error": "Title, question_id, and answer_id are required"}), 400

    new_form, error = FormController.create_form(
        title=title,
        description=description,
        user_id=user.id,
        question_id=question_id,
        answer_id=answer_id,
        is_public=is_public
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form created successfully",
        "form": new_form.to_dict()
    }), 201

@form_bp.route('', methods=['GET'])
@jwt_required()
def get_all_forms():
    """Get all forms"""
    forms = FormController.get_all_forms()
    return jsonify([form.to_dict() for form in forms]), 200

@form_bp.route('/public', methods=['GET'])
@jwt_required()
def get_public_forms():
    """Get public forms"""
    forms = FormController.get_public_forms()
    return jsonify([form.to_dict() for form in forms]), 200

@form_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_forms():
    """Get forms created by current user"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    forms = FormController.get_forms_by_user(user.id)
    return jsonify([form.to_dict() for form in forms]), 200

@form_bp.route('/<int:form_id>', methods=['GET'])
@jwt_required()
def get_form(form_id):
    """Get a specific form"""
    form = FormController.get_form(form_id)
    if form:
        return jsonify(form.to_dict()), 200
    return jsonify({"error": "Form not found"}), 404

@form_bp.route('/<int:form_id>', methods=['PUT'])
@jwt_required()
def update_form(form_id):
    """Update a form"""
    data = request.get_json()
    updated_form, error = FormController.update_form(
        form_id,
        **{k: v for k, v in data.items() if k in ['title', 'description', 'question_id', 'answer_id', 'is_public']}
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form updated successfully",
        "form": updated_form.to_dict()
    }), 200

@form_bp.route('/<int:form_id>', methods=['DELETE'])
@jwt_required()
def delete_form(form_id):
    """Delete a form"""
    success, error = FormController.delete_form(form_id)
    if success:
        return jsonify({"message": "Form deleted successfully"}), 200
    return jsonify({"error": error}), 404

@form_bp.route('/search', methods=['GET'])
@jwt_required()
def search_forms():
    """Search forms"""
    query = request.args.get('query')
    user_id = request.args.get('user_id', type=int)
    is_public = request.args.get('is_public', type=bool)
    
    forms = FormController.search_forms(query, user_id, is_public)
    return jsonify([form.to_dict() for form in forms]), 200