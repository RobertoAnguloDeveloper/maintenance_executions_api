from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.role_permission_service import RolePermissionService
from app import db
import logging

logger = logging.getLogger(__name__)

class RolePermissionController:
    @staticmethod
    def get_all_role_permissions():
        return RolePermissionService.get_all_role_permissions()

    @staticmethod
    def assign_permission_to_role(role_id, permission_id):
        return RolePermissionService.assign_permission_to_role(role_id, permission_id)
    
    @staticmethod
    def bulk_assign_permissions(role_id: int, permission_ids: List[int], current_user: User) -> tuple:
        """
        Bulk assign permissions to a role.
        
        Args:
            role_id (int): ID of the role
            permission_ids (list): List of permission IDs to assign
            current_user (User): Current user object for authorization
            
        Returns:
            tuple: (Created RolePermission objects or None, Error message)
        """
        return RolePermissionService.bulk_assign_permissions(
            role_id=role_id,
            permission_ids=permission_ids,
            current_user=current_user
        )
    
    @staticmethod
    def update_role_permission(role_permission_id, new_role_id, new_permission_id):
        return RolePermissionService.update_role_permission(role_permission_id, new_role_id, new_permission_id)

    @staticmethod
    def remove_permission_from_role(role_permission_id: int, username: str) -> tuple[bool, Union[Dict, str]]:
        """
        Remove a permission from a role.
        
        Args:
            role_permission_id (int): ID of the role-permission mapping
            username (str): Username of the user performing the action
            
        Returns:
            tuple: (Success boolean, Dict with deletion stats or error message)
        """
        return RolePermissionService.remove_permission_from_role(
            role_permission_id,
            username
        )

    @staticmethod
    def get_permissions_by_role(role_id):
        return RolePermissionService.get_permissions_by_role(role_id)
    
    @staticmethod
    def get_permissions_by_user(user_id):
        return RolePermissionService.get_permissions_by_user(user_id)

    @staticmethod
    def get_roles_by_permission(permission_id):
        return RolePermissionService.get_roles_by_permission(permission_id)

    @staticmethod
    def get_role_permission(role_permission_id):
        return RolePermissionService.get_role_permission(role_permission_id)