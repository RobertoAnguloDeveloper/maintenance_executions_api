from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.role_permission_controller import RolePermissionController
from app.models.role import Role
from app.models.role_permission import RolePermission
import logging

from app.services.auth_service import AuthService
from app.utils.permission_manager import EntityType, PermissionManager, RoleType

logger = logging.getLogger(__name__)

role_permission_bp = Blueprint('role_permissions', __name__)

@role_permission_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)
def get_all_role_permissions():
    """Get all role-permission mappings - Admin only"""
    try:
        role_permissions = RolePermissionController.get_all_role_permissions()
        
        return jsonify([rp.to_dict() for rp in role_permissions]), 200
    except Exception as e:
        logger.error(f"Error getting role permissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@role_permission_bp.route('/roles_with_permissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def get_roles_with_permissions():
    """Get all roles with their permissions"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        
        roles = Role.query.filter_by(is_deleted=False).all()
        result = []
        
        for role in roles:
            # Skip super user roles for non-admin users
            if role.is_super_user and not current_user_obj.role.is_super_user:
                continue
                
            role_data = role.to_dict()
            role_data['permissions'] = [
                rp.permission.to_dict() 
                for rp in role.role_permissions 
                if not rp.is_deleted and not rp.permission.is_deleted
            ]
            result.append(role_data)
            
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting roles with permissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@role_permission_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)
def assign_permission_to_role():
    """Assign permission to role - Admin only"""
    try:
        data = request.get_json()
        role_id = data.get('role_id')
        permission_id = data.get('permission_id')

        if not role_id or not permission_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Check if trying to modify admin role
        role = Role.query.get(role_id)
        if role and role.is_super_user and role_id == 1:
            return jsonify({"error": "Cannot modify the main administrator role"}), 403

        role_permission, error = RolePermissionController.assign_permission_to_role(role_id, permission_id)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Permission {permission_id} assigned to role {role_id}")
        return jsonify({
            "message": "Permission assigned to role successfully", 
            "role_permission": role_permission.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error assigning permission to role: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@role_permission_bp.route('/bulk-assign', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can bulk assign permissions
def bulk_assign_permissions():
    """Bulk assign permissions to a role - Admin only"""
    try:
        data = request.get_json()
        role_id = data.get('role_id')
        permission_ids = data.get('permission_ids', [])

        if not role_id or not permission_ids:
            return jsonify({
                "error": "Missing required fields. Need role_id and permission_ids"
            }), 400

        if not isinstance(permission_ids, list):
            return jsonify({
                "error": "permission_ids must be a list of permission IDs"
            }), 400

        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        created_mappings, error = RolePermissionController.bulk_assign_permissions(
            role_id=role_id,
            permission_ids=permission_ids,
            current_user=user
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Bulk permission assignment successful by user {current_user}")
        return jsonify({
            "message": "Permissions assigned successfully",
            "role_permissions": [
                mapping.to_dict() for mapping in created_mappings
            ]
        }), 201

    except Exception as e:
        logger.error(f"Error in bulk permission assignment: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@role_permission_bp.route('/<int:role_permission_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)
def update_role_permission(role_permission_id):
    """Update role-permission mapping - Admin only"""
    try:
        data = request.get_json()
        new_role_id = data.get('role_id')
        new_permission_id = data.get('permission_id')

        if not new_role_id or not new_permission_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Check if trying to modify admin role
        if new_role_id == 1:  # Admin role ID
            return jsonify({"error": "Cannot modify the main administrator role"}), 403

        updated_role_permission, error = RolePermissionController.update_role_permission(
            role_permission_id, new_role_id, new_permission_id
        )
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Role permission {role_permission_id} updated successfully")
        return jsonify({
            "message": "Role permission updated successfully",
            "role_permission": updated_role_permission.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error updating role permission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@role_permission_bp.route('/<int:role_permission_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)
def remove_permission_from_role(role_permission_id):
    """Remove a permission from a role with soft delete"""
    try:
        current_user = get_jwt_identity()

        success, result = RolePermissionController.remove_permission_from_role(
            role_permission_id,
            current_user
        )
        
        if success:
            logger.info(f"Role-Permission {role_permission_id} deleted by {current_user}")
            return jsonify({
                "message": "Permission removed from role successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error removing permission from role: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@role_permission_bp.route('/role/<int:role_id>/permissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def get_permissions_by_role(role_id):
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)

        role_info, permissions = RolePermissionController.get_permissions_by_role(role_id)
        if not role_info:
            return jsonify({"error": "Role not found"}), 404
            
        if role_info['id'] == 1 and not current_user_obj.role.is_super_user:
            return jsonify({"error": "Unauthorized access"}), 403

        return jsonify({
            "role": role_info,
            "permissions": permissions
        }), 200
    except Exception as e:
        logger.error(f"Error getting permissions for role {role_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@role_permission_bp.route('/permission/<int:permission_id>/roles', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def get_roles_by_permission(permission_id):
   try:
       current_user = get_jwt_identity()
       current_user_obj = AuthService.get_current_user(current_user)

       permission_info, roles = RolePermissionController.get_roles_by_permission(permission_id)
       if not permission_info:
           return jsonify({"error": "Permission not found"}), 404

       if not current_user_obj.role.is_super_user:
           roles = [role for role in roles if not role.get('is_super_user')]

       return jsonify({
           "permission": permission_info,
           "roles": roles
       }), 200
   except Exception as e:
       logger.error(f"Error getting roles for permission {permission_id}: {str(e)}")
       return jsonify({"error": "Internal server error"}), 500