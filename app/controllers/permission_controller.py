from app.services.permission_service import PermissionService

class PermissionController:
    @staticmethod
    def create_permission(name, action, entity, description):
        return PermissionService.create_permission(name, action, entity, description)

    @staticmethod
    def get_permission(permission_id):
        return PermissionService.get_permission(permission_id)

    @staticmethod
    def get_permission_by_name(name):
        return PermissionService.get_permission_by_name(name)

    @staticmethod
    def get_all_permissions():
        return PermissionService.get_all_permissions()
    
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of permissions with pagination
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, permissions)
        """
        return PermissionService.get_batch(page, per_page, **filters)

    @staticmethod
    def update_permission(permission_id, name=None, action=None, entity=None, description=None):
        return PermissionService.update_permission(permission_id, name, action, entity, description)

    @staticmethod
    def delete_permission(permission_id):
        return PermissionService.delete_permission(permission_id)

    @staticmethod
    def assign_permission_to_role(permission_id, role_id):
        return PermissionService.assign_permission_to_role(permission_id, role_id)
    
    @staticmethod
    def user_has_permission(user_id, permission_name):
        return PermissionService.user_has_permission(user_id, permission_name)

    @staticmethod
    def bulk_create_permissions(permissions_data):
        return PermissionService.bulk_create_permissions(permissions_data)

    @staticmethod
    def remove_permission_from_role(permission_id, role_id):
        return PermissionService.remove_permission_from_role(permission_id, role_id)