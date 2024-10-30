from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.question_controller import QuestionController

question_bp = Blueprint('questions', __name__)

@question_bp.route('', methods=['POST'])
@jwt_required()
def create_question():
    """Create a new question"""
    data = request.get_json()
    text = data.get('text')
    question_type_id = data.get('question_type_id')
    order_number = data.get('order_number')
    has_remarks = data.get('has_remarks', False)

    if not all([text, question_type_id]):
        return jsonify({"error": "Text and question_type_id are required"}), 400

    new_question, error = QuestionController.create_question(
        text=text,
        question_type_id=question_type_id,
        order_number=order_number,
        has_remarks=has_remarks
    )
    
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Question created successfully",
        "question": new_question.to_dict()
    }), 201

@question_bp.route('', methods=['GET'])
@jwt_required()
def get_all_questions():
    """Get all questions"""
    questions = QuestionController.get_all_questions()
    return jsonify([q.to_dict() for q in questions]), 200

@question_bp.route('/type/<int:type_id>', methods=['GET'])
@jwt_required()
def get_questions_by_type(type_id):
    """Get questions by type"""
    questions = QuestionController.get_questions_by_type(type_id)
    return jsonify([q.to_dict() for q in questions]), 200

@question_bp.route('/<int:question_id>', methods=['GET'])
@jwt_required()
def get_question(question_id):
    """Get a specific question"""
    question = QuestionController.get_question(question_id)
    if question:
        return jsonify(question.to_dict()), 200
    return jsonify({"error": "Question not found"}), 404

@question_bp.route('/<int:question_id>', methods=['PUT'])
@jwt_required()
def update_question(question_id):
    """Update a question"""
    data = request.get_json()
    updated_question, error = QuestionController.update_question(
        question_id,
        **{k: v for k, v in data.items() if k in ['text', 'question_type_id', 'order_number', 'has_remarks']}
    )
    
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Question updated successfully",
        "question": updated_question.to_dict()
    }), 200

@question_bp.route('/<int:question_id>', methods=['DELETE'])
@jwt_required()
def delete_question(question_id):
    """Delete a question"""
    success, error = QuestionController.delete_question(question_id)
    if success:
        return jsonify({"message": "Question deleted successfully"}), 200
    return jsonify({"error": error}), 404

@question_bp.route('/reorder', methods=['PUT'])
@jwt_required()
def reorder_questions():
    """Reorder questions"""
    data = request.get_json()
    questions_order = data.get('questions_order', [])
    
    if not questions_order:
        return jsonify({"error": "Questions order is required"}), 400

    success, error = QuestionController.reorder_questions(questions_order)
    if success:
        return jsonify({"message": "Questions reordered successfully"}), 200
    return jsonify({"error": error}), 400