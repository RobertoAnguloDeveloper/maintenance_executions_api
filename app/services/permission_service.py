from typing import Optional, Union
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
    def create_permission(name, action, entity, description):
        try:
            current_time = datetime.utcnow()
            new_permission = Permission(
                name=name,
                action=action,
                entity=entity, 
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
    def bulk_create_permissions(permissions_data: list[dict]) -> tuple[Optional[list[Permission]], Optional[str]]:
        """Create multiple permissions with validation"""
        try:
            created_permissions = []
            
            # Start transaction
            db.session.begin_nested()

            for data in permissions_data:
                name = data.get('name', '').strip()
                
                # Validate name
                if not name:
                    db.session.rollback()
                    return None, "Permission name cannot be empty"
                
                if ' ' in name:
                    db.session.rollback()
                    return None, "Permission name cannot contain spaces"

                # Check for existing permission
                existing = Permission.query.filter_by(
                    name=name,
                    is_deleted=False
                ).first()
                
                if existing:
                    db.session.rollback()
                    return None, f"Permission '{name}' already exists"

                permission = Permission(
                    name=name,
                    action=data.get('action'),
                    entity=data.get('entity'),
                    description=data.get('description')
                )
                db.session.add(permission)
                created_permissions.append(permission)

            # Commit all changes
            db.session.commit()
            return created_permissions, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating permissions: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def get_permission(permission_id: int) -> Optional[Permission]:
        """Get non-deleted permission by ID"""
        return Permission.query.filter_by(
            id=permission_id,
            is_deleted=False
        ).first()

    @staticmethod
    def get_permission_by_name(name: str) -> Optional[Permission]:
        """Get non-deleted permission by name"""
        return Permission.query.filter_by(
            name=name,
            is_deleted=False
        ).first()
    
    @staticmethod
    def user_has_permission(user_id: int, permission_name: str) -> bool:
        """Check if a user has a specific permission"""
        try:
            # Get non-deleted user
            user = User.query.filter_by(
                id=user_id,
                is_deleted=False
            ).first()
            
            if not user:
                return False

            # Get non-deleted role
            role = Role.query.filter_by(
                id=user.role_id,
                is_deleted=False
            ).first()
            
            if not role:
                return False

            # Super users have all permissions
            if role.is_super_user:
                return True

            # Get non-deleted permission
            permission = Permission.query.filter_by(
                name=permission_name,
                is_deleted=False
            ).first()
            
            if not permission:
                return False

            # Check active role-permission mapping
            has_permission = (RolePermission.query
                .filter_by(
                    role_id=role.id,
                    permission_id=permission.id,
                    is_deleted=False
                )
                .first() is not None)

            return has_permission

        except Exception as e:
            logger.error(f"Error checking user permission: {str(e)}")
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
            permissions = Permission.query.filter_by(is_deleted=False).all()

            logger.info(f"Number of permissions found: {len(permissions)}")
            for perm in permissions:
                logger.info(f"Permission: id={perm.id}, name={perm.name}, action={perm.action}, entity={perm.entity}, description={perm.description}")
            return permissions
        except Exception as e:
            logger.error(f"Error when getting all permissions: {str(e)}")
            return []
        
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of permissions with pagination directly from database
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, permissions)
        """
        try:
            # Calculate offset
            offset = (page - 1) * per_page if page > 0 and per_page > 0 else 0
            
            # Build base query
            query = Permission.query
            
            # Apply filters
            include_deleted = filters.get('include_deleted', False)
            if not include_deleted:
                query = query.filter(Permission.is_deleted == False)
            
            action = filters.get('action')
            if action:
                query = query.filter(Permission.action == action)
                
            entity = filters.get('entity')
            if entity:
                query = query.filter(Permission.entity == entity)
                
            # Apply role-based access control
            current_user = filters.get('current_user')
            if current_user and not current_user.role.is_super_user:
                # Non-admin users can't see admin-specific permissions
                query = query.filter(~Permission.name.startswith('admin_'))
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            permissions = query.order_by(Permission.id).offset(offset).limit(per_page).all()
            
            # Convert to dictionary representation
            permissions_data = [permission.to_dict() for permission in permissions]
            
            return total_count, permissions_data
            
        except Exception as e:
            logger.error(f"Error in permission batch pagination service: {str(e)}")
            return 0, []

    @staticmethod
    def update_permission(permission_id, name=None, action=None, entity=None, description=None):
        permission = Permission.query.get(permission_id)
        if permission:
            if name:
                permission.name = name
            if action is not None:
                permission.action = action
            if entity is not None:
                permission.entity = entity
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
    def delete_permission(permission_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a permission and associated role mappings through cascade soft delete
        
        Args:
            permission_id (int): ID of the permission to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            permission = Permission.query.filter_by(
                id=permission_id,
                is_deleted=False
            ).first()
            
            if not permission:
                return False, "Permission not found"

            # Prevent deletion of core permissions
            if permission.name.startswith('core_'):
                return False, "Cannot delete core permissions"

            # Check for active role assignments
            active_roles = (RolePermission.query
                .filter_by(
                    permission_id=permission_id,
                    is_deleted=False
                )
                .join(Role)
                .filter(Role.is_deleted == False)
                .count())
                
            if active_roles > 0:
                return False, f"Permission is used by {active_roles} active role(s)"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'role_permissions': 0
            }

            # Soft delete role-permission mappings
            role_permissions = RolePermission.query.filter_by(
                permission_id=permission_id,
                is_deleted=False
            ).all()

            for rp in role_permissions:
                rp.soft_delete()
                deletion_stats['role_permissions'] += 1

            # Finally soft delete the permission
            permission.soft_delete()

            # Commit changes
            db.session.commit()
            
            logger.info(f"Permission {permission_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting permission: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

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