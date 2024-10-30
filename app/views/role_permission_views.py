from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.role_permission_controller import RolePermissionController
from app.models.role import Role
from app.models.role_permission import RolePermission

role_permission_bp = Blueprint('role_permissions', __name__)

@role_permission_bp.route('', methods=['GET'])
@jwt_required()
def get_all_role_permissions():
    role_permissions = RolePermissionController.get_all_role_permissions()
    return jsonify([{
        "id": rp.id,
        "role": {
            "id": rp.role.id,
            "name": rp.role.name,
            "description": rp.role.description
        },
        "permission": {
            "id": rp.permission.id,
            "name": rp.permission.name,
            "description": rp.permission.description
        },
        "created_at": rp.created_at.isoformat(),
        "updated_at": rp.updated_at.isoformat()
    } for rp in role_permissions]), 200
    
@role_permission_bp.route('/roles_with_permissions', methods=['GET'])
@jwt_required()
def get_roles_with_permissions():
    roles = Role.query.all()
    result = []
    for role in roles:
        role_data = role.to_dict()
        role_data['permissions'] = [p.to_dict() for p in role.permissions]
        result.append(role_data)
    return jsonify(result), 200

@role_permission_bp.route('', methods=['POST'])
@jwt_required()
def assign_permission_to_role():
    data = request.get_json()
    role_id = data.get('role_id')
    permission_id = data.get('permission_id')

    if not role_id or not permission_id:
        return jsonify({"error": "Missing required fields"}), 400

    role_permission, error = RolePermissionController.assign_permission_to_role(role_id, permission_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Permission assigned to role successfully", 
        "role_permission": {
            "id": role_permission.id,
            "role_id": role_permission.role_id,
            "permission_id": role_permission.permission_id
        }
    }), 201
    
@role_permission_bp.route('/<int:role_permission_id>', methods=['PUT'])
@jwt_required()
def update_role_permission(role_permission_id):
    data = request.get_json()
    new_role_id = data.get('role_id')
    new_permission_id = data.get('permission_id')

    if not new_role_id or not new_permission_id:
        return jsonify({"error": "Missing required fields"}), 400

    updated_role_permission, error = RolePermissionController.update_role_permission(role_permission_id, new_role_id, new_permission_id)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Role permission updated successfully",
        "role_permission": {
            "id": updated_role_permission.id,
            "role_id": updated_role_permission.role_id,
            "permission_id": updated_role_permission.permission_id,
            "updated_at": updated_role_permission.updated_at.isoformat()
        }
    }), 200

@role_permission_bp.route('/<int:role_permission_id>', methods=['DELETE'])
@jwt_required()
def remove_permission_from_role(role_permission_id):
    success, error = RolePermissionController.remove_permission_from_role(role_permission_id)
    if success:
        return jsonify({"message": "Permission removed from role successfully"}), 200
    return jsonify({"error": error}), 404

@role_permission_bp.route('/role/<int:role_id>/permissions', methods=['GET'])
@jwt_required()
def get_permissions_by_role(role_id):
    permissions = RolePermissionController.get_permissions_by_role(role_id)
    return jsonify([{
        "id": p.id, 
        "name": p.name, 
        "description": p.description
    } for p in permissions]), 200

@role_permission_bp.route('/permission/<int:permission_id>/roles', methods=['GET'])
@jwt_required()
def get_roles_by_permission(permission_id):
    roles = RolePermissionController.get_roles_by_permission(permission_id)
    return jsonify([{
        "id": r.id, 
        "name": r.name, 
        "description": r.description
    } for r in roles]), 200