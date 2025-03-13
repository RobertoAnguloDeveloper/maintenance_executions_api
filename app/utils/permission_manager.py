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
    ROLES = "roles"
    FORMS = "forms"
    QUESTIONS = "questions"
    QUESTION_TYPES = "question_types"
    ANSWERS = "answers"
    SUBMISSIONS = "form_submissions"
    ATTACHMENTS = "attachments"
    ENVIRONMENTS = "environments"

class ActionType(Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class PermissionManager:
    # Resource ownership checking is now separate from permission checking
    # This keeps permissions clean and focused on actions and entities

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
    def has_permission(cls, user, action: str, entity_type: EntityType = None) -> bool:
        """
        Check if user has specific permission based on database Permission objects.
        For own_resource=True, checks for general permission for the action/entity.
        """
        try:
            # First check for super users who have all permissions
            if user.role.is_super_user:
                return True
                
            # For permission checking, we need a valid entity type
            if not entity_type:
                logger.warning("No entity type provided for permission check")
                return False
                
            entity_value = entity_type.value
                
            # Check database permissions
            if hasattr(user, 'role') and hasattr(user.role, 'permissions'):
                for permission in user.role.permissions:
                    # Check if action matches directly
                    if permission.action == action:
                        # Check if entity matches directly
                        if permission.entity == entity_value:
                            return True
                        
                        # Check for singular/plural variations
                        if entity_value.endswith('s') and permission.entity == entity_value[:-1]:
                            return True
                        if permission.entity.endswith('s') and entity_value == permission.entity[:-1]:
                            return True
                            
                        # Special case handling for entity types
                        if entity_value == 'submissions' and permission.entity == 'form_submissions':
                            return True
                        if entity_value == 'form_submissions' and permission.entity == 'submissions':
                            return True
            
            # If we reach here, no permission was found in the database
            return False
            
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False

    @classmethod
    def require_permission(cls, action: str, entity_type: EntityType = None, 
                         own_resource: bool = False, check_environment: bool = True):
        """
        Decorator to require specific permission.
        If own_resource=True, it will check resource ownership during the request.
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    current_user = get_jwt_identity()
                    user = AuthService.get_current_user(current_user)
                    
                    if not user:
                        return jsonify({"error": "User not found"}), 404

                    # Always check the basic permission first
                    if not cls.has_permission(user, action, entity_type):
                        # If own_resource is True and user doesn't have general permission,
                        # we'll check ownership during the actual request processing
                        if not own_resource:
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

                    # For own_resource=True, we need to check ownership
                    if own_resource:
                        # Get the resource ID from kwargs or request parameters
                        resource_id = None
                        if entity_type:
                            resource_id = kwargs.get(f"{entity_type.value[:-1]}_id")
                            if not resource_id:
                                # Try other common ID patterns if direct match not found
                                for key in kwargs:
                                    if key.endswith('_id'):
                                        resource_id = kwargs[key]
                                        break
                        
                        # Check ownership if we have a resource ID
                        if resource_id:
                            # This would be a more detailed implementation based on entity type
                            # For now, we'll just log a warning
                            logger.warning(f"Resource ownership checking not implemented for {entity_type.value if entity_type else 'unknown entity'}")
                            
                            # If user doesn't have general permission, deny access
                            # (We already checked this above, but for clarity)
                            if not cls.has_permission(user, action, entity_type):
                                return jsonify({
                                    "error": "Unauthorized",
                                    "message": f"You don't have permission to {action} this resource"
                                }), 403

                    # If we reach here, user is authorized
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
        """Get all permissions for a user from the database"""
        try:
            # Use database permissions
            if hasattr(user, 'role') and hasattr(user.role, 'permissions'):
                permissions = {}
                
                # If super user, return all permissions
                if user.role.is_super_user:
                    return {entity.value: {
                        "view": True, "create": True, "update": True, "delete": True
                    } for entity in EntityType}
                
                # Otherwise build from database permissions
                for permission in user.role.permissions:
                    entity = permission.entity
                    action = permission.action
                    
                    if entity not in permissions:
                        permissions[entity] = {}
                    permissions[entity][action] = True
                
                return permissions
            
            # Return empty dict if no permissions found
            return {}
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return {}