from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_submission_controller import FormSubmissionController

form_submission_bp = Blueprint('form_submissions', __name__)

@form_submission_bp.route('', methods=['POST'])
@jwt_required()
def create_form_submission():
    """Create a new form submission"""
    data = request.get_json()
    question_answer = data.get('question_answer')
    username = data.get('username')

    if not all([question_answer, username]):
        return jsonify({"error": "Question answer and username are required"}), 400

    new_submission, error = FormSubmissionController.create_form_submission(
        question_answer=question_answer,
        username=username
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form submission created successfully",
        "submission": new_submission.to_dict()
    }), 201

@form_submission_bp.route('', methods=['GET'])
@jwt_required()
def get_all_submissions():
    """Get all form submissions"""
    submissions = FormSubmissionController.get_all_submissions()
    return jsonify([submission.to_dict() for submission in submissions]), 200

@form_submission_bp.route('/<int:submission_id>', methods=['GET'])
@jwt_required()
def get_form_submission(submission_id):
    """Get a specific form submission"""
    submission = FormSubmissionController.get_form_submission(submission_id)
    if submission:
        return jsonify(submission.to_dict()), 200
    return jsonify({"error": "Form submission not found"}), 404

@form_submission_bp.route('/username/<string:username>', methods=['GET'])
@jwt_required()
def get_submissions_by_username(username):
    """Get submissions by username"""
    submissions = FormSubmissionController.get_submissions_by_username(username)
    return jsonify([submission.to_dict() for submission in submissions]), 200

@form_submission_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
def get_submissions_by_form(form_id):
    """Get submissions for a specific form"""
    submissions = FormSubmissionController.get_submissions_by_form(form_id)
    return jsonify([submission.to_dict() for submission in submissions]), 200

@form_submission_bp.route('/<int:submission_id>', methods=['PUT'])
@jwt_required()
def update_form_submission(submission_id):
    """Update a form submission"""
    data = request.get_json()
    updated_submission, error = FormSubmissionController.update_form_submission(
        submission_id,
        **{k: v for k, v in data.items() if k in ['question_answer', 'username']}
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Form submission updated successfully",
        "submission": updated_submission.to_dict()
    }), 200

@form_submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@jwt_required()
def delete_form_submission(submission_id):
    """Delete a form submission"""
    success, error = FormSubmissionController.delete_form_submission(submission_id)
    if success:
        return jsonify({"message": "Form submission deleted successfully"}), 200
    return jsonify({"error": error}), 404

@form_submission_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_submission_statistics():
    """Get submission statistics"""
    stats, error = FormSubmissionController.get_submission_statistics()
    if error:
        return jsonify({"error": error}), 400
    return jsonify(stats), 200