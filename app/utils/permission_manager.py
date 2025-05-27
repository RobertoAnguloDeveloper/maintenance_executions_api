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
        # Ensure user and user.role exist before checking super_user
        if user and hasattr(user, 'role') and user.role and user.role.is_super_user:
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
        Ensures 'action' is treated as a string.
        """
        try:
            if not user:
                logger.warning("Permission check attempted with no user object.")
                return False

            # Check if user and user.role exist, then check is_super_user
            if hasattr(user, 'role') and user.role and user.role.is_super_user:
                logger.debug(f"Permission granted to superuser: {user.username}")
                return True
                
            if not entity_type:
                logger.warning(f"No entity type provided for permission check for user: {user.username}")
                return False
                
            entity_value = entity_type.value
            action_value = str(action) # Ensure action is a string

            # Check database permissions, ensuring user.role and user.role.permissions exist
            if hasattr(user, 'role') and user.role and hasattr(user.role, 'permissions') and user.role.permissions:
                for permission in user.role.permissions:
                    # Compare string action_value with string permission.action
                    if permission.action == action_value:
                        # Check if entity matches directly
                        if permission.entity == entity_value:
                            logger.debug(f"Permission granted: User {user.username}, Action {action_value}, Entity {entity_value} (Direct match)")
                            return True
                        
                        # Check for singular/plural variations
                        if entity_value.endswith('s') and permission.entity == entity_value[:-1]:
                            logger.debug(f"Permission granted: User {user.username}, Action {action_value}, Entity {entity_value} (Plural match)")
                            return True
                        if permission.entity.endswith('s') and entity_value == permission.entity[:-1]:
                            logger.debug(f"Permission granted: User {user.username}, Action {action_value}, Entity {entity_value} (Singular match)")
                            return True
                            
                        # Special case handling for entity types
                        if entity_value == 'submissions' and permission.entity == 'form_submissions':
                            logger.debug(f"Permission granted: User {user.username}, Action {action_value}, Entity {entity_value} (Special case 'submissions')")
                            return True
                        if entity_value == 'form_submissions' and permission.entity == 'submissions':
                            logger.debug(f"Permission granted: User {user.username}, Action {action_value}, Entity {entity_value} (Special case 'form_submissions')")
                            return True
            
            # If we reach here, no permission was found
            logger.warning(f"Permission denied: User {user.username}, Action {action_value}, Entity {entity_value}. No matching permission found.")
            return False
            
        except Exception as e:
            # Log the specific error to help diagnose issues like AttributeErrors
            logger.error(f"Error checking permission for user {user.username if user else 'Unknown'}: {str(e)}", exc_info=True)
            return False

    @classmethod
    def require_permission(cls, action: Union[str, ActionType], entity_type: EntityType = None, 
                         own_resource: bool = False, check_environment: bool = True):
        """
        Decorator to require specific permission.
        Ensures the action's string value is used for checks and messages.
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    current_user_identity = get_jwt_identity()
                    # Ensure AuthService.get_current_user loads relationships (e.g., role)
                    user = AuthService.get_current_user(current_user_identity) 
                    
                    if not user:
                        return jsonify({"error": "User not found"}), 404

                    # Ensure action is its string value
                    action_str = action.value if isinstance(action, ActionType) else str(action)

                    # Pass the string value to has_permission
                    if not cls.has_permission(user, action_str, entity_type):
                        if not own_resource:
                            return jsonify({
                                "error": "Unauthorized",
                                # Use the string value in the message
                                "message": f"You don't have permission to {action_str} {entity_type.value if entity_type else ''}"
                            }), 403

                    # Check environment access if required
                    if check_environment:
                        environment_id = kwargs.get('environment_id') or request.args.get('environment_id')
                        if environment_id:
                             # Ensure environment_id is int before checking
                             try:
                                 env_id_int = int(environment_id)
                                 if not cls.check_environment_access(user, env_id_int):
                                     return jsonify({
                                         "error": "Unauthorized",
                                         "message": "You don't have access to this environment"
                                     }), 403
                             except (ValueError, TypeError):
                                 logger.warning(f"Invalid environment_id format: {environment_id}")
                                 return jsonify({"error": "Invalid environment ID format."}), 400

                    # For own_resource=True, we need to check ownership
                    if own_resource:
                        resource_id = None
                        if entity_type:
                            resource_id_key = f"{entity_type.value[:-1]}_id" if entity_type.value.endswith('s') else f"{entity_type.value}_id"
                            resource_id = kwargs.get(resource_id_key)
                            if not resource_id:
                                for key in kwargs:
                                    if key.endswith('_id'):
                                        resource_id = kwargs[key]
                                        break
                        
                        if resource_id:
                            # IMPORTANT: Resource ownership check needs proper implementation.
                            logger.warning(f"Resource ownership checking not fully implemented for {entity_type.value if entity_type else 'unknown entity'}")
                            
                            if not cls.has_permission(user, action_str, entity_type):
                                return jsonify({
                                    "error": "Unauthorized",
                                    "message": f"You don't have permission to {action_str} this resource"
                                }), 403

                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error in permission decorator: {str(e)}", exc_info=True)
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
                    current_user_identity = get_jwt_identity()
                    user = AuthService.get_current_user(current_user_identity)
                    
                    if not user:
                        return jsonify({"error": "User not found"}), 404

                    # Ensure user.role exists before checking its name or super_user status
                    if not (hasattr(user, 'role') and user.role):
                        logger.error(f"Role not found for user: {user.username}")
                        return jsonify({"error": "User role configuration error."}), 500

                    # Convert role names to strings for comparison
                    allowed_role_names = set(
                        role.value if isinstance(role, Role) else (role if isinstance(role, str) else role.value)
                        for role in allowed_roles
                    )
                    
                    if user.role.name not in allowed_role_names and not user.role.is_super_user:
                        return jsonify({
                            "error": "Unauthorized",
                            "message": f"This action requires one of these roles: {', '.join(allowed_role_names)}"
                        }), 403
                        
                    return f(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in role decorator: {str(e)}", exc_info=True)
                    return jsonify({"error": "Internal server error"}), 500
            return decorated_function
        return decorator

    @classmethod
    def get_user_permissions(cls, user) -> dict:
        """Get all permissions for a user from the database"""
        try:
            # Ensure user object and role exist
            if not user or not hasattr(user, 'role') or not user.role:
                return {}

            permissions = {}
            
            # If super user, return all permissions
            if user.role.is_super_user:
                return {entity.value: {
                    action.value: True for action in ActionType
                } for entity in EntityType}
            
            # Otherwise build from database permissions
            if hasattr(user.role, 'permissions') and user.role.permissions:
                for permission in user.role.permissions:
                    entity = permission.entity
                    action = permission.action
                    
                    if entity not in permissions:
                        permissions[entity] = {}
                    permissions[entity][action] = True
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions for {user.username if user else 'Unknown'}: {str(e)}", exc_info=True)
            return {}