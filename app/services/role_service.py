from typing import Optional
from app import db
from app.models import Role
from datetime import datetime
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.base_service import BaseService
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class RoleService(BaseService):
    def __init__(self):
        super().__init__(Role)
    
    @staticmethod
    def create_role(name, description, is_super_user=False):
        try:
            new_role = Role(
                name=name, 
                description=description, 
                is_super_user=is_super_user,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(new_role)
            db.session.commit()
            return new_role, None
        except IntegrityError as e:
            db.session.rollback()
            if "unique constraint" in str(e.orig).lower():
                return None, "Role name already exists"
            return None, str(e)
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_role(role_id: int) -> Optional[Role]:
        """Get non-deleted role by ID"""
        return Role.query.filter_by(
            id=role_id,
            is_deleted=False
        ).first()
        
    @staticmethod
    def get_users_by_role(role_id: int) -> list[User]:
        """Get all non-deleted users with specific role"""
        return User.query.filter_by(
            role_id=role_id,
            is_deleted=False
        ).all()

    @staticmethod
    def get_role_by_name(name: str) -> Optional[Role]:
        """Get non-deleted role by name"""
        return Role.query.filter_by(
            name=name,
            is_deleted=False
        ).first()
    
    @staticmethod
    def get_role_with_permissions(role_id):
        """Get non-deleted role with its permissions"""
        return Role.query.options(
            joinedload(Role.role_permissions).joinedload(RolePermission.permission)
        ).filter_by(id=role_id, is_deleted=False).first()

    @staticmethod
    def get_all_roles() -> list[Role]:
        """Get all non-deleted roles"""
        return Role.query.filter_by(is_deleted=False).order_by(Role.id).all()

    @staticmethod
    def update_role(role_id, **kwargs):
        role = Role.query.get(role_id)
        if role:
            for key, value in kwargs.items():
                if hasattr(role, key):
                    setattr(role, key, value)
            try:
                db.session.commit()
                return role, None
            except IntegrityError:
                db.session.rollback()
                return None, "A role with this name already exists"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Role not found"

    @staticmethod
    def delete_role(role_id: int) -> tuple[bool, Optional[str]]:
        """
        Delete a role and its associated data through cascade soft delete
        
        Args:
            role_id (int): ID of the role to delete
            
        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        try:
            role = Role.query.filter_by(
                id=role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return False, "Role not found"

            # Check if it's the main admin role
            if role.is_super_user and role_id == 1:
                return False, "Cannot delete the main administrator role"

            # Check for active users
            active_users = User.query.filter_by(
                role_id=role_id,
                is_deleted=False
            ).count()
            
            if active_users > 0:
                return False, f"Cannot delete role with {active_users} active users"

            # Start transaction
            db.session.begin_nested()

            # 1. Soft delete role permissions
            RolePermission.query.filter_by(
                role_id=role_id,
                is_deleted=False
            ).update({
                'is_deleted': True,
                'deleted_at': datetime.utcnow()
            })

            # 2. Soft delete the role itself
            role.soft_delete()

            # Commit all changes
            db.session.commit()
            logger.info(f"Role {role_id} and associated permissions soft deleted")
            return True, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting role: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def add_permission_to_role(role_id: int, permission_id: int) -> tuple[bool, Optional[str]]:
        """Add permission to role with proper validation"""
        try:
            # Verify role exists and is not deleted
            role = Role.query.filter_by(id=role_id, is_deleted=False).first()
            if not role:
                return False, "Role not found or inactive"

            # Verify permission exists and is not deleted
            permission = Permission.query.filter_by(id=permission_id, is_deleted=False).first()
            if not permission:
                return False, "Permission not found or inactive"

            # Check if relationship already exists and is not deleted
            existing = RolePermission.query.filter_by(
                role_id=role_id,
                permission_id=permission_id,
                is_deleted=False
            ).first()
            
            if existing:
                return False, "Permission already assigned to role"

            # Create new relationship
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            db.session.add(role_permission)
            db.session.commit()

            return True, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error adding permission to role: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def remove_permission_from_role(role_id: int, permission_id: int) -> tuple[bool, Optional[str]]:
        """Soft delete role-permission relationship"""
        try:
            role_permission = RolePermission.query.filter_by(
                role_id=role_id,
                permission_id=permission_id,
                is_deleted=False
            ).first()

            if not role_permission:
                return False, "Role-Permission relationship not found"

            role_permission.soft_delete()
            db.session.commit()

            return True, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error removing permission from role: {str(e)}"
            logger.error(error_msg)
            return False, error_msg