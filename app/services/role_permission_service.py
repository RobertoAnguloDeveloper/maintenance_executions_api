from typing import Dict, List, Optional, Tuple, Union
from app import db
from app.models.role_permission import RolePermission
from app.models.role import Role
from app.models.permission import Permission
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from datetime import datetime
from app.models.user import User
from app.services.base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class RolePermissionService(BaseService):
    def __init__(self):
        super().__init__(RolePermission)
    
    @staticmethod
    def get_all_role_permissions():
        return RolePermission.query.filter_by(is_deleted=False).all()

    @staticmethod
    def assign_permission_to_role(
        role_id: int,
        permission_id: int,
        current_user: User
    ) -> Tuple[Optional[RolePermission], Optional[str]]:
        """
        Assign a permission to a role with comprehensive validation.
        
        Args:
            role_id: ID of the role
            permission_id: ID of the permission
            current_user: Current user object for authorization
            
        Returns:
            tuple: (Created RolePermission object or None, Error message or None)
        """
        try:
            # Verify role exists and is not deleted
            role = Role.query.filter_by(
                id=role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return None, "Role not found or has been deleted"

            # Prevent modification of admin role
            if role.is_super_user and role_id == 1:  # Admin role ID
                return None, "Cannot modify permissions of the main administrator role"

            # Verify permission exists and is not deleted
            permission = Permission.query.filter_by(
                id=permission_id,
                is_deleted=False
            ).first()
            
            if not permission:
                return None, "Permission not found or has been deleted"

            # Start transaction
            db.session.begin_nested()

            # Check for existing non-deleted mapping
            existing = RolePermission.query.filter_by(
                role_id=role_id,
                permission_id=permission_id,
                is_deleted=False
            ).first()
            
            if existing:
                return None, "Permission is already assigned to this role"

            # Create new role-permission mapping
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            db.session.add(role_permission)
            db.session.commit()

            logger.info(
                f"Assigned permission {permission_id} to role {role_id} "
                f"by user {current_user.username}"
            )
            return role_permission, None

        except IntegrityError as e:
            db.session.rollback()
            error_msg = "Database integrity error: possibly invalid IDs"
            logger.error(f"{error_msg}: {str(e)}")
            return None, error_msg
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error assigning permission: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def bulk_assign_permissions(
        role_id: int,
        permission_ids: List[int],
        current_user: User
    ) -> Tuple[Optional[List[RolePermission]], Optional[str]]:
        """
        Bulk assign permissions to a role with transaction safety.
        
        Args:
            role_id: ID of the role
            permission_ids: List of permission IDs
            current_user: Current user object for authorization
            
        Returns:
            tuple: (List of created RolePermission objects or None, Error message or None)
        """
        try:
            # Verify role exists and is not deleted
            role = Role.query.filter_by(
                id=role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return None, "Role not found or has been deleted"

            # Prevent modification of admin role
            if role.is_super_user and role_id == 1:
                return None, "Cannot modify permissions of the main administrator role"

            # Start transaction
            db.session.begin_nested()

            created_mappings = []

            # Validate all permissions first
            for permission_id in permission_ids:
                permission = Permission.query.filter_by(
                    id=permission_id,
                    is_deleted=False
                ).first()
                
                if not permission:
                    db.session.rollback()
                    return None, f"Permission {permission_id} not found or deleted"

            # Create mappings for non-existing combinations
            for permission_id in permission_ids:
                existing = RolePermission.query.filter_by(
                    role_id=role_id,
                    permission_id=permission_id,
                    is_deleted=False
                ).first()
                
                if not existing:
                    mapping = RolePermission(
                        role_id=role_id,
                        permission_id=permission_id
                    )
                    db.session.add(mapping)
                    created_mappings.append(mapping)

            db.session.commit()
            
            logger.info(
                f"Bulk assigned {len(created_mappings)} permissions to role {role_id} "
                f"by user {current_user.username}"
            )
            return created_mappings, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error in bulk permission assignment: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        
    @staticmethod
    def update_role_permission(role_permission_id, new_role_id, new_permission_id):
        role_permission = RolePermission.query.filter_by(id=role_permission_id, is_deleted=False).first()
        if role_permission:
            try:
                role_permission.role_id = new_role_id
                role_permission.permission_id = new_permission_id
                role_permission.updated_at = datetime.utcnow()
                db.session.commit()
                return role_permission, None
            except IntegrityError:
                db.session.rollback()
                return None, "Invalid role_id or permission_id, or this combination already exists"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "RolePermission not found"

    @staticmethod
    def remove_permission_from_role(
        role_permission_id: int,
        username: str
    ) -> Tuple[bool, Union[Dict, str]]:
        """
        Remove a permission from a role with cascade soft delete.
        
        Args:
            role_permission_id: ID of the role-permission mapping
            username: Username of the user performing the action
            
        Returns:
            tuple: (Success boolean, Dict with deletion stats or error message)
        """
        try:
            # Verify mapping exists and is not deleted
            role_permission = RolePermission.query.filter_by(
                id=role_permission_id,
                is_deleted=False
            ).first()
            
            if not role_permission:
                return False, "Role-Permission mapping not found or has been deleted"

            # Prevent modification of admin role
            if role_permission.role_id == 1:
                return False, "Cannot modify permissions of the main administrator role"

            # Start transaction
            db.session.begin_nested()

            # Capture deletion details before soft delete
            deletion_stats = {
                'role_permission_id': role_permission.id,
                'role': {
                    'id': role_permission.role_id,
                    'name': role_permission.role.name
                },
                'permission': {
                    'id': role_permission.permission_id,
                    'name': role_permission.permission.name
                },
                'deleted_at': datetime.utcnow().isoformat()
            }

            # Soft delete the mapping
            role_permission.is_deleted = True
            role_permission.deleted_at = datetime.utcnow()
            
            db.session.commit()

            logger.info(
                f"Removed permission {role_permission.permission_id} from role "
                f"{role_permission.role_id} by user {username}"
            )
            return True, {'role_permissions': [deletion_stats]}

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error removing permission: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        
    @staticmethod
    def check_user_has_permission(
        user: User,
        permission_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a user has a specific permission through their role.
        
        Args:
            user: User object to check
            permission_name: Name of the permission
            
        Returns:
            tuple: (Has permission boolean, Error message or None)
        """
        try:
            # Super users have all permissions
            if user.role.is_super_user:
                return True, None

            # Verify permission exists and is not deleted
            permission = Permission.query.filter_by(
                name=permission_name,
                is_deleted=False
            ).first()
            
            if not permission:
                return False, "Permission not found or has been deleted"

            # Check if user's role has the permission
            role_permission = RolePermission.query.filter_by(
                role_id=user.role_id,
                permission_id=permission.id,
                is_deleted=False
            ).first()

            return bool(role_permission), None

        except Exception as e:
            error_msg = f"Error checking permission: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def bulk_assign_permissions(
        role_id: int,
        permission_ids: List[int],
        current_user: User
    ) -> Tuple[Optional[List[RolePermission]], Optional[str]]:
        """
        Bulk assign permissions to a role with transaction safety.
        
        Args:
            role_id: ID of the role
            permission_ids: List of permission IDs
            current_user: Current user object for authorization
            
        Returns:
            tuple: (List of created RolePermission objects or None, Error message or None)
        """
        try:
            # Verify role exists and is not deleted
            role = Role.query.filter_by(
                id=role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return None, "Role not found or has been deleted"

            # Prevent modification of admin role
            if role.is_super_user and role_id == 1:
                return None, "Cannot modify permissions of the main administrator role"

            # Start transaction
            db.session.begin_nested()

            created_mappings = []

            # Validate all permissions first
            for permission_id in permission_ids:
                permission = Permission.query.filter_by(
                    id=permission_id,
                    is_deleted=False
                ).first()
                
                if not permission:
                    db.session.rollback()
                    return None, f"Permission {permission_id} not found or deleted"

            # Create mappings for non-existing combinations
            for permission_id in permission_ids:
                existing = RolePermission.query.filter_by(
                    role_id=role_id,
                    permission_id=permission_id,
                    is_deleted=False
                ).first()
                
                if not existing:
                    mapping = RolePermission(
                        role_id=role_id,
                        permission_id=permission_id
                    )
                    db.session.add(mapping)
                    created_mappings.append(mapping)

            db.session.commit()
            
            logger.info(
                f"Bulk assigned {len(created_mappings)} permissions to role {role_id} "
                f"by user {current_user.username}"
            )
            return created_mappings, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error in bulk permission assignment: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def check_role_has_permission(role_id, permission_id):
        role_permission = RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first()
        return role_permission is not None

    @staticmethod
    def get_permissions_by_role(role_id):
        role = Role.query.get(role_id)
        if not role:
            return None, None
            
        role_permissions = RolePermission.query.filter_by(
            role_id=role_id,
            is_deleted=False
        ).join(Permission).filter(
            Permission.is_deleted==False
        ).all()
        
        return role, [rp.permission for rp in role_permissions]
    
    @staticmethod
    def get_permissions_by_user(user_id: int) -> list[Permission]:
        """Get all permissions for a user through their role with proper validation"""
        try:
            user = (User.query
                .join(Role, Role.id == User.role_id)
                .filter(
                    User.id == user_id,
                    User.is_deleted == False,
                    Role.is_deleted == False
                ).first())
            
            if not user:
                return []

            # Super users have all non-deleted permissions
            if user.role.is_super_user:
                return Permission.query.filter_by(is_deleted=False).all()

            # Get permissions through role-permission relationship
            return (Permission.query
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .filter(
                    Role.id == user.role_id,
                    Permission.is_deleted == False,
                    RolePermission.is_deleted == False,
                    Role.is_deleted == False
                )
                .order_by(Permission.name)
                .all())
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {str(e)}")
            return []

    @staticmethod
    def get_roles_by_permission(permission_id):
        permission = Permission.query.get(permission_id)
        if not permission:
            return None, None
            
        role_permissions = RolePermission.query.filter_by(
            permission_id=permission_id,
            is_deleted=False
        ).join(Role).filter(
            Role.is_deleted==False
        ).all()
        
        return permission, [rp.role for rp in role_permissions]

    @staticmethod
    def get_role_permission(role_permission_id: int) -> Optional[RolePermission]:
        """Get non-deleted role-permission mapping"""
        return (RolePermission.query
            .filter_by(
                id=role_permission_id,
                is_deleted=False
            )
            .options(
                joinedload(RolePermission.role),
                joinedload(RolePermission.permission)
            )
            .first())