from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.question_type_service import QuestionTypeService

question_type_bp = Blueprint('question_types', __name__)

@question_type_bp.route('', methods=['POST'])
@jwt_required()
def create_question_type():
    """Create a new question type."""
    data = request.get_json()
    if not data or 'type' not in data:
        return jsonify({"error": "Type is required"}), 400

    question_type, error = QuestionTypeService.create_question_type(data['type'])
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Question type created successfully",
        "question_type": question_type.to_dict()
    }), 201

@question_type_bp.route('', methods=['GET'])
@jwt_required()
def get_all_question_types():
    """Get all question types."""
    question_types = QuestionTypeService.get_all_question_types()
    return jsonify([qt.to_dict() for qt in question_types]), 200

@question_type_bp.route('/<int:type_id>', methods=['GET'])
@jwt_required()
def get_question_type(type_id):
    """Get a specific question type."""
    question_type = QuestionTypeService.get_question_type(type_id)
    if not question_type:
        return jsonify({"error": "Question type not found"}), 404
    return jsonify(question_type.to_dict()), 200

@question_type_bp.route('/<int:type_id>', methods=['PUT'])
@jwt_required()
def update_question_type(type_id):
    """Update a question type."""
    data = request.get_json()
    if not data or 'type' not in data:
        return jsonify({"error": "Type is required"}), 400

    question_type, error = QuestionTypeService.update_question_type(type_id, data['type'])
    if error:
        if error == "Question type not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Question type updated successfully",
        "question_type": question_type.to_dict()
    }), 200

@question_type_bp.route('/<int:type_id>', methods=['DELETE'])
@jwt_required()
def delete_question_type(type_id):
    """Delete a question type."""
    success, error = QuestionTypeService.delete_question_type(type_id)
    if not success:
        if error == "Question type not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 400

    return jsonify({"message": "Question type deleted successfully"}), 200