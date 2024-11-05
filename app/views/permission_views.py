from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.permission_controller import PermissionController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

permission_bp = Blueprint('permissions', __name__)

@permission_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can create permissions
def create_permission():
    """Create a new permission - Admin only"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')

        if not name:
            return jsonify({"error": "Name is required"}), 400

        # Validate permission name format
        if not name.islower() or ' ' in name:
            return jsonify({
                "error": "Permission name must be lowercase without spaces"
            }), 400

        new_permission, error = PermissionController.create_permission(name, description)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Permission '{name}' created successfully")
        return jsonify({
            "message": "Permission created successfully", 
            "permission": new_permission.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating permission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@permission_bp.route('/bulk-create', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can bulk create permissions
def bulk_create_permissions():
    """Bulk create permissions - Admin only"""
    try:
        data = request.get_json()
        permissions_data = data.get('permissions', [])
        
        if not permissions_data:
            return jsonify({"error": "No permissions provided"}), 400
            
        # Validate all permission names
        for perm_data in permissions_data:
            name = perm_data.get('name')
            if not name:
                return jsonify({"error": "Name is required for all permissions"}), 400
            if not name.islower() or ' ' in name:
                return jsonify({
                    "error": f"Invalid permission name format: {name}"
                }), 400
        
        new_permissions, error = PermissionController.bulk_create_permissions(permissions_data)
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"Bulk created {len(new_permissions)} permissions")
        return jsonify({
            "message": f"{len(new_permissions)} permissions created successfully",
            "permissions": [p.to_dict() for p in new_permissions]
        }), 201

    except Exception as e:
        logger.error(f"Error in bulk permission creation: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def get_all_permissions():
    """Get all permissions with role-based filtering"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        permissions = PermissionController.get_all_permissions()
        
        # Filter sensitive permissions for non-admin users
        if not user.role.is_super_user:
            permissions = [p for p in permissions if not p.name.startswith('admin_')]

        return jsonify([perm.to_dict() for perm in permissions]), 200

    except Exception as e:
        logger.error(f"Error getting permissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('/<int:permission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def get_permission(permission_id):
    """Get a specific permission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        permission = PermissionController.get_permission(permission_id)
        if not permission:
            return jsonify({"error": "Permission not found"}), 404

        # Check access to admin permissions
        if not user.role.is_super_user and permission.name.startswith('admin_'):
            return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(permission.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting permission {permission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('/check/<int:user_id>/<string:permission_name>', methods=['GET'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN, RoleType.SITE_MANAGER)
def check_user_permission(user_id, permission_name):
    """Check if a user has a specific permission"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)

        # Site Managers can only check users in their environment
        if not current_user_obj.role.is_super_user:
            user_to_check = AuthService.get_user_by_id(user_id)
            if not user_to_check or user_to_check.environment_id != current_user_obj.environment_id:
                return jsonify({"error": "Unauthorized"}), 403

        has_permission = PermissionController.user_has_permission(user_id, permission_name)
        return jsonify({"has_permission": has_permission}), 200

    except Exception as e:
        logger.error(f"Error checking permission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('/<int:permission_id>/with-roles', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def get_permission_with_roles(permission_id):
    """Get permission with associated roles"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        permission = PermissionController.get_permission_with_roles(permission_id)
        if not permission:
            return jsonify({"error": "Permission not found"}), 404

        # Filter out sensitive information for non-admin users
        if not user.role.is_super_user:
            if permission['name'].startswith('admin_'):
                return jsonify({"error": "Unauthorized access"}), 403
            permission['roles'] = [
                role for role in permission['roles'] 
                if not role['is_super_user']
            ]

        return jsonify(permission), 200

    except Exception as e:
        logger.error(f"Error getting permission with roles: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('/<int:permission_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can update permissions
def update_permission(permission_id):
    """Update a permission - Admin only"""
    try:
        permission = PermissionController.get_permission(permission_id)
        if not permission:
            return jsonify({"error": "Permission not found"}), 404

        # Prevent modification of core permissions
        if permission.name.startswith('core_'):
            return jsonify({"error": "Cannot modify core permissions"}), 403

        data = request.get_json()
        name = data.get('name')
        description = data.get('description')

        # Validate new permission name
        if name and (not name.islower() or ' ' in name):
            return jsonify({
                "error": "Permission name must be lowercase without spaces"
            }), 400

        updated_permission, error = PermissionController.update_permission(
            permission_id, name, description
        )
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Permission {permission_id} updated successfully")
        return jsonify({
            "message": "Permission updated successfully",
            "permission": updated_permission.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating permission {permission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('/<int:permission_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can delete permissions
def delete_permission(permission_id):
    """Delete a permission - Admin only"""
    try:
        permission = PermissionController.get_permission(permission_id)
        if not permission:
            return jsonify({"error": "Permission not found"}), 404

        # Prevent deletion of core permissions
        if permission.name.startswith('core_'):
            return jsonify({"error": "Cannot delete core permissions"}), 403

        # Check if permission is in use
        roles_count = len(permission.roles)
        if roles_count > 0:
            return jsonify({
                "error": f"Cannot delete permission. It is used by {roles_count} role(s)"
            }), 400

        success, error = PermissionController.delete_permission(permission_id)
        if success:
            logger.info(f"Permission {permission_id} deleted successfully")
            return jsonify({"message": "Permission deleted successfully"}), 200
        return jsonify({"error": error}), 404

    except Exception as e:
        logger.error(f"Error deleting permission {permission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@permission_bp.route('/<int:permission_id>/roles/<int:role_id>', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can delete permissions
def assign_permission_to_role(permission_id, role_id):
    success, error = PermissionController.assign_permission_to_role(permission_id, role_id)
    if success:
        return jsonify({"message": "Permission assigned to role successfully"}), 200
    return jsonify({"error": error}), 400

@permission_bp.route('/<int:permission_id>/roles/<int:role_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can delete permissions
def remove_permission_from_role(permission_id, role_id):
    success, error = PermissionController.remove_permission_from_role(permission_id, role_id)
    if success:
        return jsonify({"message": "Permission removed from role successfully"}), 200
    return jsonify({"error": error}), 400