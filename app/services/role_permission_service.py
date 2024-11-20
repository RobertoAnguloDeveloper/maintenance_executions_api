from typing import Optional, Union
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
        permission_id: int
    ) -> tuple[Optional[RolePermission], Optional[str]]:
        """Assign permission to role with validation"""
        try:
            # Verify role exists and is not deleted
            role = Role.query.filter_by(
                id=role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return None, "Role not found or inactive"

            # Verify permission exists and is not deleted
            permission = Permission.query.filter_by(
                id=permission_id,
                is_deleted=False
            ).first()
            
            if not permission:
                return None, "Permission not found or inactive"

            # Check if relationship already exists and is not deleted
            existing = RolePermission.query.filter_by(
                role_id=role_id,
                permission_id=permission_id,
                is_deleted=False
            ).first()
            
            if existing:
                return None, "Permission already assigned to role"

            # Create new relationship
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            db.session.add(role_permission)
            db.session.commit()

            return role_permission, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error assigning permission to role: {str(e)}"
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
    def remove_permission_from_role(role_permission_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Remove permission from role through soft delete
        
        Args:
            role_permission_id (int): ID of the role-permission mapping to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            role_permission = RolePermission.query.filter_by(
                id=role_permission_id,
                is_deleted=False
            ).first()
            
            if not role_permission:
                return False, "Role-Permission mapping not found"

            # Check if it's a core admin role permission
            if role_permission.role_id == 1:  # Assuming 1 is admin role ID
                return False, "Cannot modify permissions of the main administrator role"

            # Check if it's a core permission
            if role_permission.permission.name.startswith('core_'):
                return False, "Cannot remove core permissions from roles"

            # Start transaction
            db.session.begin_nested()

            # Soft delete the role-permission mapping
            role_permission.soft_delete()

            # Commit changes
            db.session.commit()
            
            logger.info(f"Role-Permission mapping {role_permission_id} soft deleted")
            return True, {"role_permissions": 1}

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error removing permission from role: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def bulk_assign_permissions(
        role_id: int,
        permission_ids: list[int]
    ) -> tuple[bool, Optional[str]]:
        """Bulk assign permissions to a role"""
        try:
            # Verify role exists and is not deleted
            role = Role.query.filter_by(
                id=role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return False, "Role not found or inactive"

            # Start transaction
            db.session.begin_nested()

            for permission_id in permission_ids:
                # Skip if mapping already exists
                existing = RolePermission.query.filter_by(
                    role_id=role_id,
                    permission_id=permission_id,
                    is_deleted=False
                ).first()
                
                if not existing:
                    role_permission = RolePermission(
                        role_id=role_id,
                        permission_id=permission_id
                    )
                    db.session.add(role_permission)

            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error bulk assigning permissions: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def check_role_has_permission(role_id, permission_id):
        role_permission = RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first()
        return role_permission is not None

    @staticmethod
    def get_permissions_by_role(role_id: int) -> list[Permission]:
        """Get all non-deleted permissions for a role"""
        return (Permission.query
            .join(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                Permission.is_deleted == False,
                RolePermission.is_deleted == False
            )
            .all())
    
    @staticmethod
    def get_permissions_by_user(user_id: int) -> list[Permission]:
        """Get all non-deleted permissions for a user through their role"""
        user = User.query.filter_by(
            id=user_id,
            is_deleted=False
        ).first()
        
        if not user or not user.role_id:
            return []

        # Super users have all permissions
        if user.role.is_super_user:
            return Permission.query.filter_by(is_deleted=False).all()

        return (Permission.query
            .join(RolePermission)
            .filter(
                RolePermission.role_id == user.role_id,
                Permission.is_deleted == False,
                RolePermission.is_deleted == False
            )
            .all())

    @staticmethod
    def get_roles_by_permission(permission_id: int) -> list[Role]:
        """Get all non-deleted roles that have a specific permission"""
        return (Role.query
            .join(RolePermission)
            .filter(
                RolePermission.permission_id == permission_id,
                Role.is_deleted == False,
                RolePermission.is_deleted == False
            )
            .all())

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