# app/utils/permission_manager.py

from enum import Enum
from typing import Optional, List, Union
from functools import wraps
from flask_jwt_extended import get_jwt_identity
from flask import jsonify, request, current_app
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)
    
class RoleType:
    """Role type constants"""
    ADMIN = "Admin"
    SITE_MANAGER = "Site Manager"
    SUPERVISOR = "Supervisor"
    TECHNICIAN = "Technician"
    
class Role(Enum):
    """Role enum for type safety"""
    ADMIN = RoleType.ADMIN
    SITE_MANAGER = RoleType.SITE_MANAGER
    SUPERVISOR = RoleType.SUPERVISOR
    TECHNICIAN = RoleType.TECHNICIAN
    
    @staticmethod
    def get_value(role_name: str) -> str:
        """Get role value by name"""
        try:
            return Role[role_name.upper().replace(" ", "_")].value
        except KeyError:
            return None

class EntityType(Enum):
    USERS = "users"
    ROLES = "roles"  # Added this
    FORMS = "forms"
    QUESTIONS = "questions"
    QUESTION_TYPES = "question_types"
    ANSWERS = "answers"
    SUBMISSIONS = "submissions"
    ATTACHMENTS = "attachments"
    ENVIRONMENTS = "environments"  # Added this line

class ActionType(Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class PermissionManager:
    ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "permissions": "*",  # All permissions
        "environment_restricted": False
    },
    Role.SITE_MANAGER: {
        "permissions": [
            "view_users", "update_users", "delete_users",
            "view_forms", "create_forms", "update_forms", "delete_forms",
            "view_environments",  # Added environment permissions
            "view_questions", "create_questions", "update_questions", "delete_questions",
            "view_submissions", "create_submissions", "update_submissions", "delete_submissions"
        ],
        "environment_restricted": True
    },
    Role.SUPERVISOR: {
        "permissions": [
            "view_forms", "create_forms", "update_forms", "delete_forms",
            "view_environments",  # Added environment view permission
            "view_submissions", "update_submissions"
        ],
        "environment_restricted": True
    },
    Role.TECHNICIAN: {
        "permissions": [
            "view_public_forms",
            "view_environments",  # Added environment view permission
            "create_submissions",
            "view_own_submissions",
            "update_own_submissions",
            "delete_own_submissions",
            "create_attachments",
            "view_own_attachments",
            "update_own_attachments",
            "delete_own_attachments"
        ],
        "environment_restricted": True
    }
}

    @staticmethod
    def check_environment_access(user, environment_id: int) -> bool:
        """Check if user has access to the specified environment"""
        if user.role.is_super_user:
            return True
        return user.environment_id == environment_id

    @staticmethod
    def check_resource_ownership(user, resource) -> bool:
        """Check if user owns the resource"""
        if hasattr(resource, 'user_id'):
            return resource.user_id == user.id
        if hasattr(resource, 'submitted_by'):
            return resource.submitted_by == user.username
        if hasattr(resource, 'creator_id'):
            return resource.creator_id == user.id
        return False

    @classmethod
    def has_permission(cls, user, action: str, entity_type: EntityType = None, 
                      own_resource: bool = False) -> bool:
        """Check if user has specific permission"""
        try:
            if user.role.is_super_user:
                return True

            #role_config = cls.ROLE_PERMISSIONS.get(Role(user.role.name))
            
            # if not role_config:
            #     return False

            # if role_config["permissions"] == "*":
            #     return True

            permission_name = f"{action}"
            if own_resource:
                permission_name = f"{action}_own"
            if entity_type:
                permission_name = f"{permission_name}_{entity_type.value}"
                
            return permission_name

            # return permission_name in role_config["permissions"]
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False

    @classmethod
    def require_permission(cls, action: str, entity_type: EntityType = None, 
                         own_resource: bool = False, check_environment: bool = True):
        """Decorator to require specific permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    current_user = get_jwt_identity()
                    user = AuthService.get_current_user(current_user)
                    
                    if not user:
                        return jsonify({"error": "User not found"}), 404

                    # Check basic permission
                    if not cls.has_permission(user, action, entity_type, own_resource):
                        return jsonify({
                            "error": "Unauthorized",
                            "message": f"You don't have permission to {action} {entity_type.value if entity_type else ''}"
                        }), 403

                    # Check environment access if required
                    if check_environment:
                        environment_id = kwargs.get('environment_id') or request.args.get('environment_id')
                        if environment_id and not cls.check_environment_access(user, int(environment_id)):
                            return jsonify({
                                "error": "Unauthorized",
                                "message": "You don't have access to this environment"
                            }), 403

                    return f(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in permission decorator: {str(e)}")
                    return jsonify({"error": "Internal server error"}), 500
            return decorated_function
        return decorator

    @classmethod
    def require_role(cls, *allowed_roles: Union[str, RoleType]):
        """Decorator to require specific roles"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    current_user = get_jwt_identity()
                    user = AuthService.get_current_user(current_user)
                    
                    if not user:
                        return jsonify({"error": "User not found"}), 404

                    # Convert role names to strings for comparison
                    allowed_role_names = set(
                        role if isinstance(role, str) else role
                        for role in allowed_roles
                    )
                    
                    if user.role.name not in allowed_role_names and not user.role.is_super_user:
                        return jsonify({
                            "error": "Unauthorized",
                            "message": f"This action requires one of these roles: {', '.join(allowed_role_names)}"
                        }), 403
                        
                    return f(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in role decorator: {str(e)}")
                    return jsonify({"error": "Internal server error"}), 500
            return decorated_function
        return decorator

    @classmethod
    def get_user_permissions(cls, user) -> dict:
        """Get all permissions for a user"""
        try:
            role_config = cls.ROLE_PERMISSIONS.get(Role(user.role.name))
            if not role_config:
                return {}

            if role_config["permissions"] == "*":
                return {entity.value: {
                    "view": True, "create": True, "update": True, "delete": True,
                    "view_own": True, "update_own": True, "delete_own": True
                } for entity in EntityType}

            permissions = {}
            for permission in role_config["permissions"]:
                parts = permission.split('_')
                action = parts[0]
                entity = '_'.join(parts[1:])
                
                if entity not in permissions:
                    permissions[entity] = {}
                permissions[entity][action] = True

            return permissions
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return {}