from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers import form_controller
from app.controllers.form_controller import FormController
from app.controllers.user_controller import UserController
from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.services.auth_service import AuthService
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from app import db

form_bp = Blueprint('forms', __name__)

@form_bp.route('', methods=['GET'])
@jwt_required()
def get_all_forms():
    """Get all forms with optional filters"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Add query parameters for filtering
    is_public = request.args.get('is_public', type=bool)
    
    # If user is not admin, only return public forms and their own forms
    if not user.role.is_super_user:
        forms = FormController.get_forms_by_user_or_public(user.id, is_public)
    else:
        forms = FormController.get_all_forms(is_public=is_public)

    return jsonify([form.to_dict() for form in forms]), 200

@form_bp.route('/<int:form_id>', methods=['GET'])
@jwt_required()
def get_form(form_id):
    """Get a specific form"""
    form = FormController.get_form(form_id)
    if not form:
        return jsonify({"error": "Form not found"}), 404

    return jsonify(form.to_dict()), 200

@form_bp.route('/creator/<string:username>', methods=['GET'])
@jwt_required()
def get_forms_by_creator(username):
    """Get all forms created by a specific user"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Users can only see their own forms unless they're admin
    if not user.role.is_super_user and current_user != username:
        return jsonify({"error": "Unauthorized access"}), 403

    forms = FormController.get_forms_by_creator(username)
    if forms is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify([form.to_dict() for form in forms]), 200
    
@form_bp.route('/environment/<int:environment_id>', methods=['GET'])
@jwt_required()
def get_forms_by_environment(environment_id):
    """Get all forms associated with an environment"""
    print(f"Accessing forms for environment ID: {environment_id}")  # Debug log
    
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    print(f"Current user: {user.username}, Environment: {user.environment_id}")  # Debug log

    # If user is not admin, they can only see forms from their environment
    if not user.role.is_super_user and user.environment_id != environment_id:
        print(f"Unauthorized access attempt by {user.username}")  # Debug log
        return jsonify({"error": "Unauthorized access"}), 403

    forms = FormController.get_forms_by_environment(environment_id)
    
    if forms is None:
        print(f"Environment {environment_id} not found")  # Debug log
        return jsonify({"error": "Environment not found"}), 404

    print(f"Found {len(forms)} forms for environment {environment_id}")  # Debug log
    return jsonify([{
        'id': form.id,
        'title': form.title,
        'description': form.description,
        'is_public': form.is_public,
        'created_at': form.created_at.isoformat() if form.created_at else None,
        'updated_at': form.updated_at.isoformat() if form.updated_at else None,
        'creator': {
            'id': form.creator.id,
            'username': form.creator.username,
            'environment_id': form.creator.environment.id,
            'environment_name': form.creator.environment.name
        } if form.creator else None,
        'questions_count': len(form.form_questions),
        'submissions_count': len(form.submissions)
    } for form in forms]), 200
    
@staticmethod
def get_forms_by_user_or_public(user_id, is_public=None):
    """Get forms created by user or public forms"""
    query = Form.query.filter(
        db.or_(
            Form.user_id == user_id,
            Form.is_public == True
        )
    ).options(
        joinedload(Form.creator),
        joinedload(Form.form_questions)
            .joinedload(FormQuestion.question)
            .joinedload(Question.question_type)
    )
    
    if is_public is not None:
        query = query.filter_by(is_public=is_public)
        
    return query.order_by(Form.created_at.desc()).all()
    
@form_bp.route('/public', methods=['GET'])
@jwt_required()
def get_public_forms():
    """Get all public forms"""
    forms = FormController.get_public_forms()
    return jsonify([form.to_dict() for form in forms]), 200

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
    
    if submissions is None:
        return jsonify({"error": "Form not found"}), 404
        
    return jsonify([{
        'id': submission.id,
        'form_id': submission.form_id,
        'submitted_by': submission.submitted_by,
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
        'answers': [{
            'question': answer.form_answer.form_question.question.text,
            'answer': answer.form_answer.answer.value,
            'remarks': answer.form_answer.remarks
        } for answer in submission.answers_submitted],
        'attachments': [{
            'id': attachment.id,
            'file_type': attachment.file_type,
            'file_path': attachment.file_path,
            'is_signature': attachment.is_signature
        } for attachment in submission.attachments]
    } for submission in submissions]), 200

@form_bp.route('/<int:form_id>/statistics', methods=['GET'])
@jwt_required()
def get_form_statistics(form_id):
    """Get statistics for a specific form"""
    stats = FormController.get_form_statistics(form_id)
    return jsonify(stats), 200

@form_bp.route('/<int:form_id>', methods=['PUT'])
@jwt_required()
def update_form(form_id):
    """Update a form's details"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Get the form
    form = FormController.get_form(form_id)
    if not form:
        return jsonify({"error": "Form not found"}), 404
        
    # Check permissions
    if not user.role.is_super_user and form.user_id != user.id:
        return jsonify({"error": "Unauthorized to modify this form"}), 403

    data = request.get_json()
    allowed_fields = ['title', 'description', 'is_public', 'user_id']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    # Additional validation for user_id changes
    if 'user_id' in update_data:
        # Check if the target user exists
        target_user = UserController.get_user(update_data['user_id'])
        if not target_user:
            return jsonify({"error": "Target user not found"}), 404
        
        # Only super users can change form ownership
        if not user.role.is_super_user:
            return jsonify({"error": "Only administrators can change form ownership"}), 403

    # Update the form
    updated_form, error = FormController.update_form(form_id, **update_data)
    
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify({
        "message": "Form updated successfully",
        "form": updated_form.to_dict()
    }), 200