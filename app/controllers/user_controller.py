from app.services.user_service import UserService

class UserController:
    def __init__(self):
        self.user_service = UserService()
        
    @staticmethod
    def create_user(first_name, last_name, email, username, password, role_id, environment_id):
        return UserService.create_user(first_name, last_name, email, username, password, role_id, environment_id)

    @staticmethod
    def get_user(user_id):
        return UserService.get_user(user_id)

    @staticmethod
    def get_user_by_username(username):
        return UserService.get_user_by_username(username)

    @staticmethod
    def get_all_users(include_deleted=False):
        return UserService.get_all_users_with_relations(include_deleted=include_deleted)
    
    @staticmethod
    def search_users(username=None, role_id=None, environment_id=None):
        return UserService.search_users(username, role_id, environment_id)

    @staticmethod
    def update_user(user_id, **kwargs):
        return UserService.update_user(user_id, **kwargs)

    @staticmethod
    def delete_user(user_id):
        return UserService.delete_user(user_id)

    @staticmethod
    def get_users_by_role(role_id):
        return UserService.get_users_by_role(role_id)
    
    @staticmethod
    def get_users_by_role_and_environment(role_id, enviornment_id):
        return UserService.get_users_by_role_and_environment(role_id, enviornment_id)
    
    @staticmethod
    def get_users_by_environment(environment_id):
        return UserService.get_users_by_environment(environment_id)