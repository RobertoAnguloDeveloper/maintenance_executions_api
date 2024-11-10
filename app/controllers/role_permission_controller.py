from app.services.role_permission_service import RolePermissionService

class RolePermissionController:
    @staticmethod
    def get_all_role_permissions():
        return RolePermissionService.get_all_role_permissions()

    @staticmethod
    def assign_permission_to_role(role_id, permission_id):
        return RolePermissionService.assign_permission_to_role(role_id, permission_id)
    
    @staticmethod
    def update_role_permission(role_permission_id, new_role_id, new_permission_id):
        return RolePermissionService.update_role_permission(role_permission_id, new_role_id, new_permission_id)

    @staticmethod
    def remove_permission_from_role(role_permission_id):
        return RolePermissionService.remove_permission_from_role(role_permission_id)

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