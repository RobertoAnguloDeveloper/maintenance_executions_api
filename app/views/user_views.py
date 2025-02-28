from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.environment_controller import EnvironmentController
from app.controllers.role_controller import RoleController
from app.controllers.user_controller import UserController
from app.models.role import Role
from app.services.auth_service import AuthService
from sqlalchemy.exc import IntegrityError
from app.models.environment import Environment
import logging

from app.utils.permission_manager import EntityType, PermissionManager, RoleType

logger = logging.getLogger(__name__)

user_bp = Blueprint('users', __name__)

@user_bp.route('/register', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.USERS)
@PermissionManager.require_role(RoleType.ADMIN)
def register_user():
    """Create a new user - Admin and Site Manager only"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)

        data = request.get_json()
        required_fields = ['first_name', 'last_name', 'email', 'contact_number', 'username', 'password', 'role_id', 'environment_id']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate password
        if len(data['password']) < 8:
            return jsonify({"error": "Password must be at least 8 characters long"}), 400

        # Role-based validation
        if not current_user_obj.role.is_super_user:
            # Site Managers can only create users in their environment
            if data['environment_id'] != current_user_obj.environment_id:
                return jsonify({"error": "Cannot create users for other environments"}), 403
            
            # Site Managers cannot create admin users
            new_role = Role.query.get(data['role_id'])
            if new_role and new_role.is_super_user:
                return jsonify({"error": "Cannot create admin users"}), 403

        new_user, error = UserController.create_user(**data)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"User {data['username']} created successfully by {current_user}")
        return jsonify({
            "message": "User created successfully", 
            "user": new_user.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400
        
        if not UserController.get_user_by_username(username):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = AuthService.authenticate_user(username, password)
        if access_token:
            logger.info(f"User {username} logged in successfully")
            return jsonify({"access_token": access_token}), 200
            
        return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.USERS)
def get_all_users():
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        if not current_user_obj:
            return jsonify({"error": "User not found"}), 404

        # Only admins can see deleted users
        include_deleted = (current_user_obj.role.is_super_user and 
                         request.args.get('include_deleted', '').lower() == 'true')

        try:
            if current_user_obj.role.is_super_user:
                users = UserController.get_all_users(include_deleted=include_deleted)
            else:
                # Non-admin users only see active users in their environment
                users = UserController.get_users_by_environment(current_user_obj.environment_id)
                

            return jsonify([
                user.to_dict(
                    include_details=True,
                    include_deleted=current_user_obj.role.is_super_user
                ) for user in users
            ]), 200

        except Exception as e:
            logger.error(f"Database error while fetching users: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error in get_all_users: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@user_bp.route('/byRole/<int:role_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.USERS)
def get_users_by_role(role_id):
    """Get users by role with environment restrictions"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)

        if current_user_obj.role.is_super_user:
            users = UserController.get_users_by_role(role_id)
        else:
            # Filter by both role and environment
            users = UserController.get_users_by_role_and_environment(role_id, current_user_obj.environment_id)
            #return users

        return jsonify([user.to_dict() for user in users]), 200

    except Exception as e:
        logger.error(f"Error getting users by role: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
    
@user_bp.route('/byEnvironment/<int:environment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.USERS)
def get_users_by_environment(environment_id):
    """Get users by environment with access control"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)

        # Check environment access
        if not current_user_obj.role.is_super_user and current_user_obj.environment_id != environment_id:
            return jsonify({"error": "Unauthorized access to environment"}), 403

        users = UserController.get_users_by_environment(environment_id)
        return jsonify([user.to_dict() for user in users]), 200

    except Exception as e:
        logger.error(f"Error getting users by environment: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@user_bp.route('/search', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.USERS)
def search_users():
    current_user = get_jwt_identity()
    if not AuthService.get_current_user(current_user).role.is_super_user:
        return jsonify({"error": "Unauthorized"}), 403

    # Check if parameters are in URL or in JSON body
    if request.is_json:
        data = request.get_json()
        id = data.get('id')
        username = data.get('username')
        role_id = data.get('role_id')
        environment_id = data.get('environment_id')
    else:
        id = request.args.get('id')
        username = request.args.get('username')
        role_id = request.args.get('role_id')
        environment_id = request.args.get('environment_id')

    users = UserController.search_users(id, username, role_id, environment_id)
    return jsonify([user.to_dict(include_details=True) for user in users]), 200

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
@PermissionManager.require_permission(action="update", entity_type=EntityType.USERS)
def update_user(user_id):
    """Update user with role-based restrictions"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        
        # Get the user to be updated
        user_to_update = UserController.get_user(user_id)
        if not user_to_update:
            return jsonify({"error": "User not found"}), 404

        # Role-based access control
        if not current_user_obj.role.is_super_user:
            # Can only update users in same environment
            if user_to_update.environment_id != current_user_obj.environment_id:
                return jsonify({"error": "Cannot update users from other environments"}), 403
                
            # Cannot update admin users
            if user_to_update.role.is_super_user:
                return jsonify({"error": "Cannot update admin users"}), 403

        data = request.get_json()
        allowed_fields = ['first_name', 'last_name', 'email','contact_number', 'password']
        
        # Only admins can update these fields
        if current_user_obj.role.is_super_user:
            allowed_fields.extend(['username', 'role_id', 'environment_id'])
            
        update_fields = {k: v for k, v in data.items() if k in allowed_fields}
        
        updated_user, error = UserController.update_user(user_id, **update_fields)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"User {user_id} updated successfully by {current_user}")
        return jsonify({
            "message": "User updated successfully",
            "user": updated_user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.USERS)
def delete_user(user_id):
    """Delete user with cascade soft delete"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)

        # Get the user to be deleted (with is_deleted=False check)
        user_to_delete = UserController.get_user(user_id)
        if not user_to_delete:
            return jsonify({"error": "User not found"}), 404

        # Security validations
        if not current_user_obj.role.is_super_user:
            # Can only delete users in same environment
            if user_to_delete.environment_id != current_user_obj.environment_id:
                return jsonify({"error": "Cannot delete users from other environments"}), 403
                
            # Cannot delete admin users
            if user_to_delete.role.is_super_user:
                return jsonify({"error": "Cannot delete admin users"}), 403
            
            # Cannot delete themselves
            if user_to_delete.id == current_user_obj.id:
                return jsonify({"error": "Cannot delete own account"}), 403

        success, result = UserController.delete_user(user_id)
        if success:
            logger.info(f"User {user_id} and all associated data deleted by {current_user}")
            return jsonify({
                "message": "User and all associated data deleted successfully",
                "deleted_items": result
            }), 200
            
        return jsonify({"error": result}), 400

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user details"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        if user:
            return jsonify(user.to_dict(include_details=True, include_deleted=False)), 200
            
        return jsonify({"error": "User not found"}), 404

    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500