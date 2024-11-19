from app import db
from app.controllers.role_permission_controller import RolePermissionController
from app.models import Permission
from datetime import datetime
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.base_service import BaseService
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

class PermissionService(BaseService):
    def __init__(self):
        super().__init__(Permission)
    
    @staticmethod
    def create_permission(name, description):
        try:
            current_time = datetime.utcnow()
            new_permission = Permission(
                name=name, 
                description=description,
                created_at=current_time,
                updated_at=current_time
            )
            db.session.add(new_permission)
            db.session.commit()
            logger.info(f"Created new permission: {name}")
            return new_permission, None
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"IntegrityError when creating permission: {name}. Error: {str(e)}")
            return None, "A permission with this name already exists"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error when creating permission: {name}. Error: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def bulk_create_permissions(permissions_data):
        try:
            new_permissions = []
            for p_data in permissions_data:
                new_permission = Permission(
                    name=p_data['name'],
                    description=p_data.get('description')
                )
                new_permissions.append(new_permission)
            
            db.session.bulk_save_objects(new_permissions)
            db.session.commit()
            return new_permissions, None
        except IntegrityError:
            db.session.rollback()
            return None, "One or more permission names already exist"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_permission(permission_id):
        return Permission.query.get(permission_id)

    @staticmethod
    def get_permission_by_name(name):
        return Permission.get_by_name(name)
    
    @staticmethod
    def user_has_permission(user_id, permission_name):
        user = User.query.get(user_id)
        if not user:
            return False
        
        user_permissions = RolePermissionController.get_permissions_by_user(user_id)
        
        for permission in user_permissions:
            if permission.name == permission_name:
                return True
        
        return False

            
    @staticmethod
    def get_permission_with_roles(permission_id):
        permission = Permission.query.options(db.joinedload(Permission.role_permissions).joinedload(RolePermission.role)).get(permission_id)
        if permission:
            permission_dict = permission.to_dict()
            permission_dict['roles'] = [rp.role.to_dict() for rp in permission.role_permissions]
            return permission_dict
        return None

    @staticmethod
    def get_all_permissions():
        try:
            permissions = Permission.query.order_by(Permission.id).all()
            logger.info(f"Number of permissions found: {len(permissions)}")
            for perm in permissions:
                logger.info(f"Permission: id={perm.id}, name={perm.name}")
            return permissions
        except Exception as e:
            logger.error(f"Error when getting all permissions: {str(e)}")
            return []

    @staticmethod
    def update_permission(permission_id, name=None, description=None):
        permission = Permission.query.get(permission_id)
        if permission:
            if name:
                permission.name = name
            if description is not None:
                permission.description = description
            try:
                db.session.commit()
                return permission, None
            except IntegrityError:
                db.session.rollback()
                return None, "A permission with this name already exists"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Permission not found"

    @staticmethod
    def delete_permission(permission_id):
        permission = Permission.query.get(permission_id)
        if permission:
            try:
                db.session.delete(permission)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Permission not found"

    @staticmethod
    def add_permission_to_role(role_id, permission_id):
        role = Role.query.get(role_id)
        permission = Permission.query.get(permission_id)
        if not role:
            return False, "Role not found"
        if not permission:
            return False, "Permission not found"
        if permission in role.permissions:
            return False, "Permission already assigned to role"
        role.permissions.append(permission)
        db.session.commit()
        return True, "Permission added to role successfully"

    @staticmethod
    def remove_permission_from_role(permission_id, role_id):
        permission = Permission.query.get(permission_id)
        role = Role.query.get(role_id)
        if permission and role:
            permission.remove_from_role(role)
            db.session.commit()
            return True, None
        return False, "Permission or Role not found"