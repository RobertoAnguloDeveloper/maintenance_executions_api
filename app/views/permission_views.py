from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.controllers.permission_controller import PermissionController

permission_bp = Blueprint('permissions', __name__)

@permission_bp.route('', methods=['POST'])
@jwt_required()
def create_permission():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({"error": "Name is required"}), 400

    new_permission, error = PermissionController.create_permission(name, description)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Permission created successfully", 
        "permission": {
            "id": new_permission.id,
            "name": new_permission.name,
            "description": new_permission.description
        }
    }), 201
    
@permission_bp.route('/bulk-create', methods=['POST'])
@jwt_required()
def bulk_create_permissions():
    data = request.get_json()
    permissions_data = data.get('permissions', [])
    
    if not permissions_data:
        return jsonify({"error": "No permissions provided"}), 400
    
    new_permissions, error = PermissionController.bulk_create_permissions(permissions_data)
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify({
        "message": f"{len(new_permissions)} permissions created successfully",
        "permissions": [p.to_dict() for p in new_permissions]
    }), 201

@permission_bp.route('', methods=['GET'])
@jwt_required()
def get_all_permissions():
    try:
        permissions = PermissionController.get_all_permissions()
        print(f"Número de permisos retornados: {len(permissions)}")
        return jsonify([perm.to_dict() for perm in permissions]), 200
    except Exception as e:
        print(f"Error al obtener permisos: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

@permission_bp.route('/<int:permission_id>', methods=['GET'])
@jwt_required()
def get_permission(permission_id):
    permission = PermissionController.get_permission(permission_id)
    if permission:
        return jsonify({
            "id": permission.id, 
            "name": permission.name, 
            "description": permission.description
        }), 200
    return jsonify({"error": "Permission not found"}), 404

@permission_bp.route('/check/<int:user_id>/<string:permission_name>', methods=['GET'])
@jwt_required()
def check_user_permission(user_id, permission_name):
    has_permission = PermissionController.user_has_permission(user_id, permission_name)
    return jsonify({"has_permission": has_permission}), 200

@permission_bp.route('/<int:permission_id>/with-roles', methods=['GET'])
@jwt_required()
def get_permission_with_roles(permission_id):
    permission = PermissionController.get_permission_with_roles(permission_id)
    if permission:
        return jsonify(permission), 200
    return jsonify({"error": "Permission not found"}), 404

@permission_bp.route('/<int:permission_id>', methods=['PUT'])
@jwt_required()
def update_permission(permission_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    updated_permission, error = PermissionController.update_permission(permission_id, name, description)
    if error:
        return jsonify({"error": error}), 400
    
    if updated_permission:
        return jsonify({
            "message": "Permission updated successfully", 
            "permission": {
                "id": updated_permission.id,
                "name": updated_permission.name,
                "description": updated_permission.description
            }
        }), 200
    return jsonify({"error": "Permission not found"}), 404

@permission_bp.route('/<int:permission_id>', methods=['DELETE'])
@jwt_required()
def delete_permission(permission_id):
    success, error = PermissionController.delete_permission(permission_id)
    if success:
        return jsonify({"message": "Permission deleted successfully"}), 200
    return jsonify({"error": error}), 404

@permission_bp.route('/<int:permission_id>/roles/<int:role_id>', methods=['POST'])
@jwt_required()
def assign_permission_to_role(permission_id, role_id):
    success, error = PermissionController.assign_permission_to_role(permission_id, role_id)
    if success:
        return jsonify({"message": "Permission assigned to role successfully"}), 200
    return jsonify({"error": error}), 400

@permission_bp.route('/<int:permission_id>/roles/<int:role_id>', methods=['DELETE'])
@jwt_required()
def remove_permission_from_role(permission_id, role_id):
    success, error = PermissionController.remove_permission_from_role(permission_id, role_id)
    if success:
        return jsonify({"message": "Permission removed from role successfully"}), 200
    return jsonify({"error": error}), 400