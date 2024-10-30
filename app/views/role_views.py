from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.role_controller import RoleController

role_bp = Blueprint('roles', __name__)

@role_bp.route('', methods=['POST'])
@jwt_required()
def create_role():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    is_super_user = data.get('is_super_user', False)

    if not name:
        return jsonify({"error": "Name is required"}), 400

    new_role, error = RoleController.create_role(name, description, is_super_user)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Role created successfully", 
        "role": new_role.to_dict()
    }), 201

@role_bp.route('', methods=['GET'])
@jwt_required()
def get_all_roles():
    roles = RoleController.get_all_roles()
    return jsonify([{
        "id": role.id, 
        "name": role.name, 
        "description": role.description, 
        "is_super_user": role.is_super_user
    } for role in roles]), 200

@role_bp.route('/<int:role_id>', methods=['GET'])
@jwt_required()
def get_role(role_id):
    role = RoleController.get_role(role_id)
    if role:
        return jsonify({
            "id": role.id, 
            "name": role.name, 
            "description": role.description, 
            "is_super_user": role.is_super_user
        }), 200
    return jsonify({"error": "Role not found"}), 404

@role_bp.route('/<int:role_id>', methods=['PUT'])
@jwt_required()
def update_role(role_id):
    data = request.get_json()
    
    update_fields = {}
    for field in ['name', 'description', 'is_super_user']:
        if field in data:
            update_fields[field] = data[field]
    
    updated_role, error = RoleController.update_role(role_id, **update_fields)
    if error:
        return jsonify({"error": error}), 400
    
    if updated_role:
        return jsonify({
            "message": "Role updated successfully", 
            "role": {
                "id": updated_role.id,
                "name": updated_role.name,
                "description": updated_role.description,
                "is_super_user": updated_role.is_super_user
            }
        }), 200
    return jsonify({"error": "Role not found"}), 404

@role_bp.route('/<int:role_id>', methods=['DELETE'])
@jwt_required()
def delete_role(role_id):
    success, error = RoleController.delete_role(role_id)
    if success:
        return jsonify({"message": "Role deleted successfully"}), 200
    return jsonify({"error": error}), 404

@role_bp.route('/<int:role_id>/permissions/<int:permission_id>', methods=['POST'])
@jwt_required()
def add_permission_to_role(role_id, permission_id):
    success, message = RoleController.add_permission_to_role(role_id, permission_id)
    if success:
        return jsonify({"message": "Permission added to role successfully"}), 200
    return jsonify({"error": message}), 400

@role_bp.route('/<int:role_id>/permissions/<int:permission_id>', methods=['DELETE'])
@jwt_required()
def remove_permission_from_role(role_id, permission_id):
    if RoleController.remove_permission_from_role(role_id, permission_id):
        return jsonify({"message": "Permission removed from role successfully"}), 200
    return jsonify({"error": "Failed to remove permission from role"}), 400