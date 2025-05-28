# app/views/user_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.environment_controller import EnvironmentController
from app.controllers.role_controller import RoleController
from app.controllers.user_controller import UserController
from app.models.role import Role # Import Role model for type checks if necessary
from app.services.auth_service import AuthService
from app.services.user_service import UserService # For direct service calls if needed for validation
from sqlalchemy.exc import IntegrityError
from app.models.environment import Environment # Import Environment model
import logging

from app.utils.permission_manager import ActionType, EntityType, PermissionManager, RoleType

logger = logging.getLogger(__name__)

user_bp = Blueprint('users', __name__)

# --- NEW UNRESTRICTED ENDPOINT ---
@user_bp.route('/all-unrestricted', methods=['GET'])
# No @jwt_required() or @PermissionManager decorators for truly unrestricted access by design.
# WARNING: This endpoint exposes user data without typical permission checks.
# Secure this at the network level or via other application-specific means if deployed.
def get_all_users_unrestricted_view():
    """
    Get ALL active users from ALL environments without standard permission restrictions.
    Optionally include soft-deleted users via query parameter.
    WARNING: This endpoint can expose sensitive user data. Use with extreme caution.
    """
    try:
        include_deleted_str = request.args.get('include_deleted', 'false').lower()
        include_deleted = include_deleted_str == 'true'
        
        users = UserController.get_all_users_unrestricted(include_deleted=include_deleted)
        # Using to_dict_basic for potentially less sensitive data exposure by default.
        # Change to user.to_dict(include_details=True, include_deleted=include_deleted) if full details are absolutely necessary.
        return jsonify([user.to_dict_basic() for user in users]), 200
    except Exception as e:
        logger.error(f"Error in get_all_users_unrestricted_view: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# --- EXISTING ENDPOINTS (MODIFIED) ---
@user_bp.route('/register', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.CREATE, entity_type=EntityType.USERS)
# Removed @PermissionManager.require_role(RoleType.ADMIN) to allow Site Managers with 'create_users' permission
# The internal logic below will restrict Site Manager capabilities appropriately.
def register_user():
    """
    Create a new user.
    Admins can create any user.
    Site Managers can create users within their own environment and cannot assign Admin/SuperUser roles.
    """
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)

        if not current_user_obj:
            logger.error(f"Authenticated user '{current_user_jwt_identity}' not found in database for registration.")
            return jsonify({"error": "Authenticated user not found."}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['first_name', 'last_name', 'email', 'contact_number', 'username', 'password', 'role_id', 'environment_id']
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        # Basic field validation
        if not isinstance(data.get('username'), str) or data['username'].isspace() or len(data['username']) < 4 :
            return jsonify({"error": "Username must be a non-empty string of at least 4 characters."}), 400
        if not isinstance(data.get('password'), str) or data['password'].isspace() or len(data['password']) < 8 :
            return jsonify({"error": "Password must be a non-empty string of at least 8 characters."}), 400
        if not isinstance(data.get('email'), str) or not validate_email(data.get('email')): # Assuming validate_email helper
             return jsonify({"error": "Invalid email format."}), 400


        # Role-based validation for non-admins (e.g., Site Manager)
        if not current_user_obj.role.is_super_user:
            if data.get('environment_id') != current_user_obj.environment_id:
                return jsonify({"error": "Site Managers can only create users within their own environment"}), 403

            role_to_assign = RoleController.get_role(data.get('role_id'))
            if not role_to_assign: # Check if role exists
                return jsonify({"error": f"Role with ID {data.get('role_id')} not found."}), 400
            if role_to_assign.is_super_user:
                return jsonify({"error": "Site Managers cannot create users with Admin/SuperUser roles"}), 403
        else: # Admin is creating user, still validate role and environment existence
            role_to_assign = RoleController.get_role(data.get('role_id'))
            if not role_to_assign:
                return jsonify({"error": f"Role with ID {data.get('role_id')} not found."}), 400
        
        env_to_assign = EnvironmentController.get_environment(data.get('environment_id'))
        if not env_to_assign:
            return jsonify({"error": f"Environment with ID {data.get('environment_id')} not found."}), 400

        new_user, error = UserController.create_user(**data)
        if error:
            logger.warning(f"User creation failed for username '{data.get('username')}' by '{current_user_jwt_identity}': {error}")
            status_code = 409 if "already exists" in error.lower() else 400
            return jsonify({"error": error}), status_code

        logger.info(f"User {data['username']} created successfully by {current_user_jwt_identity}")
        return jsonify({
            "message": "User created successfully",
            "user": new_user.to_dict() # type: ignore
        }), 201

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        user_for_login = UserService.get_user_by_username(username)
        if not user_for_login:
            logger.warning(f"Login attempt for non-existent or deleted user: {username}")
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = AuthService.authenticate_user(username, password)
        if access_token:
            logger.info(f"User {username} logged in successfully")
            return jsonify({"access_token": access_token}), 200

        logger.warning(f"Failed login attempt for user: {username}")
        return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"Error during login: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@user_bp.route('/logout', methods=['POST'])
@jwt_required() # Ensures a valid token is present to get JTI for blocklisting
def logout():
    """User logout endpoint - attempts to blocklist token"""
    try:
        auth_header = request.headers.get('Authorization', '')
        token_to_blocklist = None
        if auth_header.startswith('Bearer '):
            token_to_blocklist = auth_header[7:]

        username_for_log = get_jwt_identity() # Get identity from the validated token

        success, message = UserController.logout_user(token=token_to_blocklist, username=username_for_log)

        if not success:
             logger.warning(f"Server-side blocklisting may have failed during logout for user '{username_for_log}': {message}")

        return jsonify({
            "message": "Successfully logged out",
            "status": "success" # Client should always treat this as success for UX
        }), 200

    except Exception as e:
        logger.error(f"Error during logout route execution: {str(e)}", exc_info=True)
        return jsonify({ # Still return a success-like message to client
            "message": "Successfully logged out (encountered server error)",
            "status": "success"
        }), 200

@user_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def get_all_users():
    """
    Get all users.
    Admins can see all users (optionally including deleted).
    Non-admins see active users within their own environment.
    """
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        include_deleted = (current_user_obj.role.is_super_user and
                         request.args.get('include_deleted', '').lower() == 'true')

        users_list = []
        if current_user_obj.role.is_super_user:
            users_list = UserController.get_all_users(include_deleted=include_deleted)
        else:
            # Non-admin users only see active users in their environment
            users_list = UserController.get_users_by_environment(current_user_obj.environment_id) # type: ignore

        return jsonify([
            user.to_dict( # type: ignore
                include_details=True,
                include_deleted=include_deleted # Pass admin's choice for deleted status
            ) for user in users_list
        ]), 200

    except Exception as e:
        logger.error(f"Error in get_all_users: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/batch', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def get_batch_users():
    """Get batch of users with pagination."""
    try:
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 200: per_page = 200 # Max limit

        include_deleted_str = request.args.get('include_deleted', 'false').lower()
        role_id_filter = request.args.get('role_id', type=int)
        environment_id_filter = request.args.get('environment_id', type=int)

        current_user_jwt_identity = get_jwt_identity()
        requesting_user_obj = AuthService.get_current_user(current_user_jwt_identity)

        if not requesting_user_obj:
            return jsonify({"error": "Authenticated user not found."}), 404

        final_filters = {}
        if requesting_user_obj.role.is_super_user:
            final_filters['include_deleted'] = (include_deleted_str == 'true')
            if role_id_filter is not None:
                final_filters['role_id'] = role_id_filter
            if environment_id_filter is not None:
                final_filters['environment_id'] = environment_id_filter
        else:
            final_filters['include_deleted'] = False # Non-admins never see deleted in batch
            final_filters['environment_id'] = requesting_user_obj.environment_id # type: ignore
            if role_id_filter is not None: # Allow filtering by role within their environment
                final_filters['role_id'] = role_id_filter

        total_count, users_data_list = UserController.get_batch(
            page=page,
            per_page=per_page,
            **final_filters
        )

        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
        # Ensure current_page is not out of bounds after total_pages calculation
        current_page_display = max(1, min(page, total_pages if total_pages > 0 else 1))


        return jsonify({
            "metadata": {
                "total_items": total_count,
                "total_pages": total_pages,
                "current_page": current_page_display,
                "per_page": per_page,
                "filters_applied": final_filters
            },
            "items": users_data_list
        }), 200

    except Exception as e:
        logger.error(f"Error getting batch of users: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@user_bp.route('/compact-list', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def get_all_users_compact_list():
    """Get all users with basic details (id, name, etc.), for dropdowns."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        include_deleted_for_admin = (current_user_obj.role.is_super_user and
                                   request.args.get('include_deleted', '').lower() == 'true')

        users_list = []
        if current_user_obj.role.is_super_user:
            users_list = UserController.get_users_compact_list(include_deleted=include_deleted_for_admin)
        else:
            users_list = UserController.get_users_by_environment(current_user_obj.environment_id) # type: ignore

        compact_users_data = [user.to_dict_basic() for user in users_list] # type: ignore
        return jsonify(compact_users_data), 200

    except Exception as e:
        logger.error(f"Error in get_all_users_compact_list: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/byRole/<int:role_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def get_users_by_role(role_id):
    """Get users by role, restricted by environment for non-admins."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        role = RoleController.get_role(role_id)
        if not role: # Check if the role itself exists and is not deleted
            return jsonify({"error": f"Role with ID {role_id} not found."}), 404
        # Non-admins cannot query for users in super_user roles if that role_id belongs to a super_user role
        if role.is_super_user and not current_user_obj.role.is_super_user:
            return jsonify({"error": "Unauthorized to view users for this role."}), 403


        users_list = []
        if current_user_obj.role.is_super_user:
            users_list = UserController.get_users_by_role(role_id)
        else:
            users_list = UserController.get_users_by_role_and_environment(role_id, current_user_obj.environment_id) # type: ignore

        return jsonify([user.to_dict_basic() for user in users_list]), 200

    except Exception as e:
        logger.error(f"Error getting users by role {role_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@user_bp.route('/byEnvironment/<int:environment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def get_users_by_environment(environment_id):
    """Get users by environment, with access control."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        env = EnvironmentController.get_environment(environment_id)
        if not env: # Check if the environment exists and is not deleted
            return jsonify({"error": f"Environment with ID {environment_id} not found."}), 404

        if not current_user_obj.role.is_super_user and current_user_obj.environment_id != environment_id: # type: ignore
            logger.warning(f"User '{current_user_jwt_identity}' (env: {current_user_obj.environment_id}) attempted to access users for env {environment_id}.") # type: ignore
            return jsonify({"error": "Unauthorized to access users for this environment"}), 403

        users_list = UserController.get_users_by_environment(environment_id)
        return jsonify([user.to_dict_basic() for user in users_list]), 200

    except Exception as e:
        logger.error(f"Error getting users by environment {environment_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/search', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def search_users():
    """Search users. Non-admins are restricted to their own environment."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found."}), 404

        search_params = {}
        search_params['id'] = request.args.get('id', type=int)
        search_params['username'] = request.args.get('username')
        search_params['role_id'] = request.args.get('role_id', type=int)
        requested_env_id = request.args.get('environment_id', type=int)

        if request.is_json and request.content_length and request.content_length > 0:
            data = request.get_json()
            search_params['id'] = data.get('id', search_params['id'])
            search_params['username'] = data.get('username', search_params['username'])
            search_params['role_id'] = data.get('role_id', search_params['role_id'])
            requested_env_id = data.get('environment_id', requested_env_id)
        
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        # Apply environment restriction for non-admins
        if not current_user_obj.role.is_super_user:
            if requested_env_id is not None and requested_env_id != current_user_obj.environment_id: # type: ignore
                logger.warning(f"User '{current_user_jwt_identity}' attempted to search users in environment {requested_env_id} but belongs to {current_user_obj.environment_id}.") # type: ignore
                return jsonify({"error": "Unauthorized to search users in the specified environment."}), 403
            search_params['environment_id'] = current_user_obj.environment_id # type: ignore
        elif requested_env_id is not None : # Admin provided an environment_id
             search_params['environment_id'] = requested_env_id


        users_list = UserController.search_users(**search_params)
        return jsonify([user.to_dict(include_details=True) for user in users_list]), 200
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}),500


@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.USERS)
def get_user(user_id):
    """Get specific user details, respecting environment for non-admins."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        user_to_view = UserController.get_user(user_id)
        if not user_to_view:
            return jsonify({"error": "User not found"}), 404

        if not current_user_obj.role.is_super_user:
            if user_to_view.environment_id != current_user_obj.environment_id: # type: ignore
                logger.warning(f"User '{current_user_jwt_identity}' (env: {current_user_obj.environment_id}) unauthorized to view user {user_id} (env: {user_to_view.environment_id}).") # type: ignore
                return jsonify({"error": "Unauthorized to view this user's details"}), 403

        return jsonify(user_to_view.to_dict(
            include_details=True,
            include_deleted=(current_user_obj.role.is_super_user)
        )), 200

    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.UPDATE, entity_type=EntityType.USERS)
def update_user(user_id):
    """Update user details with role-based restrictions."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        user_to_update = UserController.get_user(user_id)
        if not user_to_update:
            return jsonify({"error": "User to update not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided for update."}), 400

        allowed_fields_for_update = ['first_name', 'last_name', 'email', 'contact_number']
        if 'password' in data and data['password']:
            if not isinstance(data.get('password'), str) or data['password'].isspace() or len(data['password']) < 8 :
                 return jsonify({"error": "Password must be a non-empty string of at least 8 characters."}), 400
            allowed_fields_for_update.append('password')

        if current_user_obj.role.is_super_user:
            allowed_fields_for_update.extend(['username', 'role_id', 'environment_id'])
        else: # Non-admin restrictions
            if user_to_update.environment_id != current_user_obj.environment_id: # type: ignore
                return jsonify({"error": "Unauthorized to update users in other environments"}), 403
            if user_to_update.role and user_to_update.role.is_super_user: # type: ignore
                return jsonify({"error": "Unauthorized to update Admin/SuperUser accounts"}), 403
            if 'role_id' in data and data['role_id'] is not None:
                target_role = RoleController.get_role(data['role_id'])
                if not target_role: return jsonify({"error": f"Target role ID {data['role_id']} not found."}), 400
                if target_role.is_super_user:
                    return jsonify({"error": "Cannot assign Admin/SuperUser role"}), 403
            if 'environment_id' in data and data['environment_id'] != current_user_obj.environment_id: # type: ignore
                 return jsonify({"error": "Cannot move user to a different environment"}), 403
            if 'username' in data and data['username'] != user_to_update.username:
                 return jsonify({"error": "Only Admins can change usernames"}), 403

        update_payload = {k: v for k, v in data.items() if k in allowed_fields_for_update}
        if not update_payload:
            return jsonify({"error": "No valid or permitted fields provided for update."}), 400

        if 'role_id' in update_payload and update_payload['role_id'] is not None:
            if not RoleController.get_role(update_payload['role_id']):
                return jsonify({"error": f"Role with ID {update_payload['role_id']} not found."}), 400
        if 'environment_id' in update_payload and update_payload['environment_id'] is not None:
            if not EnvironmentController.get_environment(update_payload['environment_id']):
                return jsonify({"error": f"Environment with ID {update_payload['environment_id']} not found."}), 400

        updated_user_obj, error_msg = UserController.update_user(user_id, **update_payload)

        if error_msg:
            logger.warning(f"Update for user {user_id} by '{current_user_jwt_identity}' failed: {error_msg}")
            status_code = 409 if "already exists" in error_msg.lower() else 400
            return jsonify({"error": error_msg}), status_code

        logger.info(f"User {user_id} updated successfully by {current_user_jwt_identity}")
        return jsonify({
            "message": "User updated successfully",
            "user": updated_user_obj.to_dict() # type: ignore
        }), 200

    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.DELETE, entity_type=EntityType.USERS)
def delete_user(user_id):
    """Delete user (soft delete) with role-based restrictions."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not current_user_obj:
            return jsonify({"error": "Authenticated user not found"}), 404

        user_to_delete = UserController.get_user(user_id)
        if not user_to_delete:
            return jsonify({"error": "User to delete not found"}), 404

        if user_to_delete.id == current_user_obj.id:
            return jsonify({"error": "Cannot delete your own account"}), 403

        if not current_user_obj.role.is_super_user:
            if user_to_delete.environment_id != current_user_obj.environment_id: # type: ignore
                return jsonify({"error": "Unauthorized to delete users in other environments"}), 403
            if user_to_delete.role and user_to_delete.role.is_super_user: # type: ignore
                return jsonify({"error": "Unauthorized to delete Admin/SuperUser accounts"}), 403

        success, result_or_error = UserController.delete_user(user_id)
        if success:
            logger.info(f"User {user_id} and associated data soft-deleted by {current_user_jwt_identity}")
            return jsonify({
                "message": "User and associated data deleted successfully",
                "deleted_items_summary": result_or_error
            }), 200

        logger.warning(f"Failed to delete user {user_id} by '{current_user_jwt_identity}': {result_or_error}")
        return jsonify({"error": result_or_error}), 400

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_user_details(): # Renamed from get_current_user
    """Get current authenticated user details."""
    try:
        current_user_jwt_identity = get_jwt_identity()
        user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if user_obj:
            return jsonify(user_obj.to_dict(include_details=True, include_deleted=False)), 200

        return jsonify({"error": "Current user not found in database (token valid but user may be deleted)"}), 404

    except Exception as e:
        logger.error(f"Error getting current user details: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# Helper for email validation (can be in app/utils/helpers.py)
import re
def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None
