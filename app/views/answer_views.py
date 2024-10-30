from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.answer_controller import AnswerController

answer_bp = Blueprint('answers', __name__)

@answer_bp.route('', methods=['POST'])
@jwt_required()
def create_answer():
    """Create a new answer"""
    data = request.get_json()
    value = data.get('value')
    remarks = data.get('remarks')

    if not value:
        return jsonify({"error": "Value is required"}), 400

    new_answer, error = AnswerController.create_answer(
        value=value,
        remarks=remarks
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Answer created successfully",
        "answer": new_answer.to_dict()
    }), 201

@answer_bp.route('/bulk', methods=['POST'])
@jwt_required()
def bulk_create_answers():
    """Create multiple answers at once"""
    data = request.get_json()
    answers_data = data.get('answers', [])

    if not answers_data:
        return jsonify({"error": "No answers provided"}), 400

    new_answers, error = AnswerController.bulk_create_answers(answers_data)

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": f"{len(new_answers)} answers created successfully",
        "answers": [answer.to_dict() for answer in new_answers]
    }), 201

@answer_bp.route('', methods=['GET'])
@jwt_required()
def get_all_answers():
    """Get all answers"""
    answers = AnswerController.get_all_answers()
    return jsonify([answer.to_dict() for answer in answers]), 200

@answer_bp.route('/<int:answer_id>', methods=['GET'])
@jwt_required()
def get_answer(answer_id):
    """Get a specific answer"""
    answer = AnswerController.get_answer(answer_id)
    if answer:
        return jsonify(answer.to_dict()), 200
    return jsonify({"error": "Answer not found"}), 404

@answer_bp.route('/form/<int:form_id>', methods=['GET'])
@jwt_required()
def get_answers_by_form(form_id):
    """Get answers for a specific form"""
    answers = AnswerController.get_answers_by_form(form_id)
    return jsonify([answer.to_dict() for answer in answers]), 200

@answer_bp.route('/<int:answer_id>', methods=['PUT'])
@jwt_required()
def update_answer(answer_id):
    """Update an answer"""
    data = request.get_json()
    updated_answer, error = AnswerController.update_answer(
        answer_id,
        value=data.get('value'),
        remarks=data.get('remarks')
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Answer updated successfully",
        "answer": updated_answer.to_dict()
    }), 200

@answer_bp.route('/<int:answer_id>', methods=['DELETE'])
@jwt_required()
def delete_answer(answer_id):
    """Delete an answer"""
    success, error = AnswerController.delete_answer(answer_id)
    if success:
        return jsonify({"message": "Answer deleted successfully"}), 200
    return jsonify({"error": error}), 404