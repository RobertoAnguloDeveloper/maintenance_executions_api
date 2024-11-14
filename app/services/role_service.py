from app import db
from app.models import Role
from datetime import datetime
from app.models.permission import Permission
from app.models.role_permission import RolePermission
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
    def get_role(role_id):
        """Get non-deleted role by ID"""
        return Role.query.filter_by(id=role_id, is_deleted=False).first()

    @staticmethod
    def get_role_by_name(name):
        """Get non-deleted role by name"""
        return Role.query.filter_by(name=name, is_deleted=False).first()
    
    @staticmethod
    def get_role_with_permissions(role_id):
        """Get non-deleted role with its permissions"""
        return Role.query.options(
            joinedload(Role.role_permissions).joinedload(RolePermission.permission)
        ).filter_by(id=role_id, is_deleted=False).first()

    @staticmethod
    def get_all_roles():
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
    def delete_role(role_id):
        role = Role.query.get(role_id)
        if role:
            if role.users:
                return False, "Cannot delete role: it is still assigned to users"
            try:
                role.soft_delete()
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Role not found"

    @staticmethod
    def add_permission_to_role(role_id, permission_id):
        try:
            role = Role.query.get(role_id)
            permission = Permission.query.get(permission_id)
            if not role or not permission:
                return False, "Role or Permission not found"
            
            # Comprobar si la relación ya existe
            existing_relation = RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first()
            if existing_relation:
                return False, "This permission is already assigned to the role"
            
            new_role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
            db.session.add(new_role_permission)
            db.session.commit()
            return True, None
        except IntegrityError:
            db.session.rollback()
            return False, "This permission is already assigned to the role"
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def remove_permission_from_role(role_id, permission_id):
        role = Role.query.get(role_id)
        permission = Permission.query.get(permission_id)
        if role and permission:
            role.remove_permission(permission)
            db.session.commit()
            return True
        return False