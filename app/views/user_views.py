from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.user_controller import UserController
from app.models.role import Role
from app.services.auth_service import AuthService
from sqlalchemy.exc import IntegrityError
from app.models.environment import Environment

user_bp = Blueprint('users', __name__)

@user_bp.route('/register', methods=['POST'])
@jwt_required()
def register_user():
    current_user = get_jwt_identity()
    current_user_obj = AuthService.get_current_user(current_user)
    
    if not current_user_obj or not current_user_obj.role.is_super_user:
        return jsonify({"error": "Unauthorized. Only super users can register new users."}), 403

    data = request.get_json()
    required_fields = ['first_name', 'last_name', 'email', 'username', 'password', 'role_id', 'environment_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if len(data['password']) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400

    role = Role.query.get(data['role_id'])
    if not role:
        return jsonify({"error": f"Role with id {data['role_id']} does not exist"}), 400

    environment = Environment.query.get(data['environment_id'])
    if not environment:
        return jsonify({"error": f"Environment with id {data['environment_id']} does not exist"}), 400

    new_user, error = UserController.create_user(**data)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "User created successfully", 
        "user": {
            "id": new_user.id,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
            "username": new_user.username,
            "role_id": new_user.role_id,
            "environment_id": new_user.environment_id
        }
    }), 201

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    access_token = AuthService.authenticate_user(username, password)
    if access_token:
        return jsonify({"access_token": access_token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@user_bp.route('', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user = get_jwt_identity()
    if not AuthService.get_current_user(current_user).role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    users = UserController.get_all_users()
    return jsonify([{
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": {
            "id": user.role.id,
            "name": user.role.name,
            "description": user.role.description,
            "is_super_user": user.role.is_super_user
        } if user.role else None,
        "environment": {
            "id": user.environment.id,
            "name": user.environment.name,
            "description": user.environment.description
        } if user.environment else None
    } for user in users]), 200
    
@user_bp.route('/byRole/<int:role_id>', methods=['GET'])
@jwt_required()
def get_users_by_role(role_id):
    current_user = get_jwt_identity()
    if not AuthService.get_current_user(current_user).role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    users = UserController.get_users_by_role(role_id)
    return jsonify([{
        "id": user.id,
        "username": user.username,
        "role_id": user.role_id,
        "environment_id": user.environment_id
    } for user in users]), 200
    
    
@user_bp.route('/byEnvironment/<int:environment_id>', methods=['GET'])
@jwt_required()
def get_users_by_environment(environment_id):
    current_user = get_jwt_identity()
    current_user_obj = AuthService.get_current_user(current_user)
    
    if not current_user_obj.role.is_super_user and current_user_obj.environment_id != environment_id:
        return jsonify({"error": "Unauthorized"}), 403

    users = UserController.get_users_by_environment(environment_id)
    return jsonify([{
        "id": user.id,
        "username": user.username,
        "role": user.role.name,
        "environment_id": user.environment_id
    } for user in users]), 200
    
@user_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    current_user = get_jwt_identity()
    if not AuthService.get_current_user(current_user).role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    # Check if parameters are in URL or in JSON body
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        role_id = data.get('role_id')
        environment_id = data.get('environment_id')
    else:
        username = request.args.get('username')
        role_id = request.args.get('role_id')
        environment_id = request.args.get('environment_id')

    users = UserController.search_users(username, role_id, environment_id)
    return jsonify([{
        "id": user.id,
        "username": user.username,
        "role_id": user.role_id,
        "environment_id": user.environment_id
    } for user in users]), 200

@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = UserController.get_user(user_id)
    if user:
        return jsonify({
            "id": user.id,
            "username": user.username,
            "role_id": user.role_id,
            "environment_id": user.environment_id
        }), 200
    return jsonify({"error": "User not found"}), 404

@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    data = request.get_json()
    
    update_fields = {}
    for field in ['first_name', 'last_name', 'email', 'username', 'password', 'role_id', 'environment_id']:
        if field in data:
            update_fields[field] = data[field]
    
    updated_user, error = UserController.update_user(user_id, **update_fields)
    
    if error:
        return jsonify({"error": error}), 400
    
    if updated_user:
        return jsonify({
            "message": "User updated successfully",
            "user": {
                "id": updated_user.id,
                "first_name": updated_user.first_name,
                "last_name": updated_user.last_name,
                "email": updated_user.email,
                "username": updated_user.username,
                "role_id": updated_user.role_id,
                "environment_id": updated_user.environment_id
            }
        }), 200
    return jsonify({"error": "User not found"}), 404

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user = get_jwt_identity()
    if not AuthService.get_current_user(current_user).role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    if UserController.delete_user(user_id):
        return jsonify({"message": "User deleted"}), 200
    return jsonify({"error": "User not found"}), 404

@user_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    if user:
        return jsonify({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "username": user.username,
            "role_id": user.role_id,
            "environment_id": user.environment_id
        }), 200
    return jsonify({"error": "User not found"}), 404