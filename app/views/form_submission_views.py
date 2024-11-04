from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_submission_controller import FormSubmissionController
from app.controllers.form_controller import FormController  # Added for form validation
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.services.auth_service import AuthService
from app.utils.decorators import roles_required
from datetime import datetime
from sqlalchemy.orm import joinedload

form_submission_bp = Blueprint('form_submissions', __name__)

@form_submission_bp.route('', methods=['POST'])
@jwt_required()
def create_form_submission():
    """Create a new form submission"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['form_id', 'answers']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields. Required: form_id, answers"}), 400

    # Validate form exists
    form = FormController.get_form(data['form_id'])
    if not form:
        return jsonify({"error": "Form not found"}), 404

    # Validate answers format
    if not isinstance(data['answers'], list):
        return jsonify({"error": "Answers must be a list"}), 400

    # Create submission
    submission, error = FormSubmissionController.create_form_submission(
        form_id=data['form_id'],
        username=current_user,
        answers=data['answers'],
        attachments=data.get('attachments', [])
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form submission created successfully",
        "submission": submission.to_dict()
    }), 201

@form_submission_bp.route('', methods=['GET'])
@jwt_required()
@roles_required('Admin', 'Supervisor')
def get_all_submissions():
    """Get all form submissions with optional filters"""
    # Add query parameters for filtering
    form_id = request.args.get('form_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filters = {}
    if form_id:
        filters['form_id'] = form_id
    if start_date:
        filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')

    submissions = FormSubmissionController.get_all_submissions(**filters)
    
    return jsonify({
        "total": len(submissions),
        "submissions": [{
            'id': submission.id,
            'form': {
                'id': submission.form.id,
                'title': submission.form.title
            } if submission.form else None,
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
            } for attachment in submission.attachments],
            'created_at': submission.created_at.isoformat() if submission.created_at else None
        } for submission in submissions]
    }), 200

@form_submission_bp.route('/user/<string:username>', methods=['GET'])
@jwt_required()
def get_user_submissions(username):
    """Get submissions by username with optional filters"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Only allow users to see their own submissions unless they're admin/supervisor
    if username != current_user and not (user.role.is_super_user or user.role.name == 'Supervisor'):
        return jsonify({"error": "Unauthorized"}), 403

    # Handle query parameters
    form_id = request.args.get('form_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filters = {'username': username}
    if form_id:
        filters['form_id'] = form_id
    if start_date:
        filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')

    submissions = FormSubmissionController.get_submissions_by_user(**filters)
    return jsonify({
        "total": len(submissions),
        "submissions": [submission.to_dict() for submission in submissions]
    }), 200

@form_submission_bp.route('/<int:submission_id>', methods=['GET'])
@jwt_required()
def get_submission(submission_id):
    """Get a specific submission"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    submission = FormSubmissionController.get_form_submission(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    # Check if user has permission to view this submission
    if (submission.submitted_by != current_user and 
        not user.role.is_super_user and 
        user.role.name not in ['Supervisor', 'Admin']):
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(submission.to_dict()), 200

@form_submission_bp.route('/filled/<int:submission_id>', methods=['GET'])
@jwt_required()
def get_filled_form(submission_id):
    """
    Get a complete filled form with all its answers and attachments.
    """
    # Get the submission with all related data
    submission = FormSubmission.query.options(
        joinedload(FormSubmission.form),
        joinedload(FormSubmission.answers_submitted)
            .joinedload(AnswerSubmitted.form_answer)
            .joinedload(FormAnswer.form_question)
            .joinedload(FormQuestion.question)
            .joinedload(Question.question_type),
        joinedload(FormSubmission.answers_submitted)
            .joinedload(AnswerSubmitted.form_answer)
            .joinedload(FormAnswer.answer),
        joinedload(FormSubmission.attachments)
    ).get_or_404(submission_id)

    # Check permission
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Only allow access to:
    # - The user who submitted the form
    # - Admins
    # - Users with view_submissions permission in the same environment
    if (submission.submitted_by != current_user and 
        not user.role.is_super_user and 
        'view_submissions' not in [p.name for p in user.role.permissions]):
        return jsonify({"error": "Unauthorized access"}), 403

    # Structure the response
    filled_form = {
        "form": {
            "id": submission.form.id,
            "title": submission.form.title,
            "description": submission.form.description
        },
        "submission": {
            "id": submission.id,
            "submitted_by": submission.submitted_by,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "created_at": submission.created_at.isoformat() if submission.created_at else None,
            "updated_at": submission.updated_at.isoformat() if submission.updated_at else None
        },
        "questions_and_answers": [],
        "attachments": []
    }

    # Get all questions and their answers
    for answer_submitted in submission.answers_submitted:
        form_answer = answer_submitted.form_answer
        question = form_answer.form_question.question
        
        question_answer = {
            "question": {
                "id": question.id,
                "text": question.text,
                "type": question.question_type.type,
                "order": question.order_number,
                "has_remarks": question.has_remarks
            },
            "answer": {
                "id": form_answer.answer.id,
                "value": form_answer.answer.value,
                "remarks": form_answer.remarks
            }
        }
        filled_form["questions_and_answers"].append(question_answer)

    # Sort questions by order number
    filled_form["questions_and_answers"].sort(
        key=lambda x: x["question"]["order"]
    )

    # Get attachments
    for attachment in submission.attachments:
        attachment_data = {
            "id": attachment.id,
            "file_type": attachment.file_type,
            "file_path": attachment.file_path,
            "is_signature": attachment.is_signature,
            "created_at": attachment.created_at.isoformat() if attachment.created_at else None
        }
        filled_form["attachments"].append(attachment_data)

    return jsonify(filled_form), 200

# Endpoint to get all submissions for a specific form
@form_submission_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
def get_form_submissions(form_id):
    """Get all submissions for a specific form with optional filters"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    submitted_by = request.args.get('submitted_by')

    # Base query
    query = FormSubmission.query.filter(FormSubmission.form_id == form_id)

    # Apply filters
    if start_date:
        query = query.filter(FormSubmission.submitted_at >= start_date)
    if end_date:
        query = query.filter(FormSubmission.submitted_at <= end_date)
    if submitted_by:
        query = query.filter(FormSubmission.submitted_by == submitted_by)

    # If not admin, only show user's own submissions
    if not user.role.is_super_user and 'view_submissions' not in [p.name for p in user.role.permissions]:
        query = query.filter(FormSubmission.submitted_by == current_user)

    # Get the submissions
    submissions = query.order_by(FormSubmission.submitted_at.desc()).all()

    # Format response
    submissions_data = []
    for submission in submissions:
        submission_data = {
            "id": submission.id,
            "submitted_by": submission.submitted_by,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "answers_count": len(submission.answers_submitted),
            "has_attachments": len(submission.attachments) > 0,
            "created_at": submission.created_at.isoformat() if submission.created_at else None
        }
        submissions_data.append(submission_data)

    return jsonify({
        "form_id": form_id,
        "total_submissions": len(submissions_data),
        "submissions": submissions_data
    }), 200

@form_submission_bp.route('/<int:submission_id>/attachments', methods=['POST'])
@jwt_required()
def add_attachment(submission_id):
    """Add an attachment to a submission"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Verify submission exists and user has permission
    submission = FormSubmissionController.get_form_submission(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    if submission.submitted_by != current_user and not user.role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    required_fields = ['file_type', 'file_path', 'file_name', 'file_size']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing required fields. Required: {', '.join(required_fields)}"}), 400

    attachment, error = FormSubmissionController.add_attachment(
        submission_id=submission_id,
        file_type=data['file_type'],
        file_path=data['file_path'],
        file_name=data['file_name'],
        file_size=data['file_size'],
        is_signature=data.get('is_signature', False)
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Attachment added successfully",
        "attachment": attachment.to_dict()
    }), 201

@form_submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@jwt_required()
def delete_submission(submission_id):
    """Delete a submission"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    submission = FormSubmissionController.get_form_submission(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
        
    # Only allow users to delete their own submissions unless they're admin
    if submission.submitted_by != current_user and not user.role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    success, error = FormSubmissionController.delete_form_submission(submission_id)
    if success:
        return jsonify({"message": "Submission deleted successfully"}), 200
    return jsonify({"error": error}), 400

@form_submission_bp.route('/statistics', methods=['GET'])
@jwt_required()
@roles_required('Admin', 'Supervisor')
def get_submission_statistics():
    """Get submission statistics with optional filters"""
    form_id = request.args.get('form_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filters = {}
    if form_id:
        filters['form_id'] = form_id
    if start_date:
        filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')

    stats = FormSubmissionController.get_submission_statistics(**filters)
    return jsonify(stats), 200