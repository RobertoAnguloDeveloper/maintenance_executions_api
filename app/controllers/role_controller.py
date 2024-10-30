from app.services.role_service import RoleService

class RoleController:
    @staticmethod
    def create_role(name, description, is_super_user=False):
        role, error = RoleService.create_role(name, description, is_super_user)
        if error:
            return None, error
        return role, None

    @staticmethod
    def get_role(role_id):
        return RoleService.get_role(role_id)

    @staticmethod
    def get_role_by_name(name):
        return RoleService.get_role_by_name(name)

    @staticmethod
    def get_all_roles():
        return RoleService.get_all_roles()

    @staticmethod
    def update_role(role_id, **kwargs):
        return RoleService.update_role(role_id, **kwargs)

    @staticmethod
    def delete_role(role_id):
        return RoleService.delete_role(role_id)

    @staticmethod
    def add_permission_to_role(role_id, permission_id):
        success, message = RoleService.add_permission_to_role(role_id, permission_id)
        return success, message

    @staticmethod
    def remove_permission_from_role(role_id, permission_id):
        return RoleService.remove_permission_from_role(role_id, permission_id)