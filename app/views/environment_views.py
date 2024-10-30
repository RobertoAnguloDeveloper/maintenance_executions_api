from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.environment_controller import EnvironmentController

environment_bp = Blueprint('environments', __name__)

@environment_bp.route('', methods=['POST'])
@jwt_required()
def create_environment():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({"error": "Name is required"}), 400

    new_environment, error = EnvironmentController.create_environment(name, description)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Environment created successfully",
        "environment": new_environment.to_dict()
    }), 201

@environment_bp.route('', methods=['GET'])
@jwt_required()
def get_all_environments():
    environments = EnvironmentController.get_all_environments()
    return jsonify([env.to_dict() for env in environments]), 200

@environment_bp.route('/<int:environment_id>', methods=['GET'])
@jwt_required()
def get_environment(environment_id):
    environment = EnvironmentController.get_environment(environment_id)
    if environment:
        return jsonify(environment.to_dict()), 200
    return jsonify({"error": "Environment not found"}), 404

@environment_bp.route('/name/<string:name>', methods=['GET'])
@jwt_required()
def get_environment_by_name(name):
    environment = EnvironmentController.get_environment_by_name(name)
    if environment:
        return jsonify(environment.to_dict()), 200
    return jsonify({"error": "Environment not found"}), 404

@environment_bp.route('/<int:environment_id>', methods=['PUT'])
@jwt_required()
def update_environment(environment_id):
    data = request.get_json()
    
    updated_environment, error = EnvironmentController.update_environment(environment_id, **data)
    if error:
        return jsonify({"error": error}), 400
    
    if updated_environment:
        return jsonify({
            "message": "Environment updated successfully", 
            "environment": updated_environment.to_dict()
        }), 200
    return jsonify({"error": "Environment not found"}), 404

@environment_bp.route('/<int:environment_id>', methods=['DELETE'])
@jwt_required()
def delete_environment(environment_id):
    success, error = EnvironmentController.delete_environment(environment_id)
    if success:
        return jsonify({"message": "Environment deleted successfully"}), 200
    return jsonify({"error": error}), 404

@environment_bp.route('/<int:environment_id>/users', methods=['GET'])
@jwt_required()
def get_users_in_environment(environment_id):
    users = EnvironmentController.get_users_in_environment(environment_id)
    return jsonify([user.to_dict() for user in users]), 200

@environment_bp.route('/<int:environment_id>/forms', methods=['GET'])
@jwt_required()
def get_forms_in_environment(environment_id):
    forms = EnvironmentController.get_forms_in_environment(environment_id)
    return jsonify([form.to_dict() for form in forms]), 200