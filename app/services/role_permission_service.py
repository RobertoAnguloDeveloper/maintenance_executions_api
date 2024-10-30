from app import db
from app.models.role_permission import RolePermission
from app.models.role import Role
from app.models.permission import Permission
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.services.base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class RolePermissionService(BaseService):
    def __init__(self):
        super().__init__(RolePermission)
    
    @staticmethod
    def get_all_role_permissions():
        return RolePermission.query.order_by(RolePermission.id).all()

    @staticmethod
    def assign_permission_to_role(role_id, permission_id):
        existing = RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first()
        if existing:
            logger.info(f"Permission {permission_id} already assigned to role {role_id}")
            return None, "Permission already assigned to role"

        try:
            role_permission = RolePermission(
                role_id=role_id, 
                permission_id=permission_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(role_permission)
            db.session.commit()
            logger.info(f"Assigned permission {permission_id} to role {role_id}")
            return role_permission, None
        except IntegrityError:
            db.session.rollback()
            logger.error(f"Failed to assign permission {permission_id} to role {role_id}: Invalid role_id or permission_id")
            return None, "Invalid role_id or permission_id"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to assign permission {permission_id} to role {role_id}: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def update_role_permission(role_permission_id, new_role_id, new_permission_id):
        role_permission = RolePermission.query.get(role_permission_id)
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
    def remove_permission_from_role(role_permission_id):
        role_permission = RolePermission.query.get(role_permission_id)
        if role_permission:
            try:
                db.session.delete(role_permission)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "RolePermission not found"
    
    @staticmethod
    def bulk_assign_permissions_to_role(role_id, permission_ids):
        try:
            new_role_permissions = []
            for permission_id in permission_ids:
                if not RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first():
                    role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
                    new_role_permissions.append(role_permission)
            
            db.session.bulk_save_objects(new_role_permissions)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    @staticmethod
    def check_role_has_permission(role_id, permission_id):
        role_permission = RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first()
        return role_permission is not None

    @staticmethod
    def get_permissions_by_role(role_id):
        role = Role.query.get(role_id)
        return role.permissions if role else []

    @staticmethod
    def get_roles_by_permission(permission_id):
        permission = Permission.query.get(permission_id)
        return permission.roles if permission else []

    @staticmethod
    def get_role_permission(role_permission_id):
        return RolePermission.query.get(role_permission_id)