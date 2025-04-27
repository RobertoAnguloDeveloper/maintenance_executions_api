from app.services.auth_service import AuthService
from app.services.user_service import UserService

class UserController:
    def __init__(self):
        self.user_service = UserService()
        
    @staticmethod
    def logout_user(token=None, username=None):
        """
        Handle user logout with enhanced token extraction
        
        Args:
            token (str): Raw JWT token (optional)
            username (str): Username of the user to logout (optional)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        return AuthService.logout_user(token=token, username=username)
        
    @staticmethod
    def create_user(first_name, last_name, email, contact_number, username, password, role_id, environment_id):
        return UserService.create_user(first_name, last_name, email, contact_number, username, password, role_id, environment_id)

    @staticmethod
    def get_user(user_id):
        return UserService.get_user(user_id)

    @staticmethod
    def get_user_by_username(username):
        return UserService.get_user_by_username(username)

    @staticmethod
    def get_all_users(include_deleted):
        return UserService.get_all_users_with_relations(include_deleted=include_deleted)
    
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of users with pagination
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, users)
        """
        return UserService.get_batch(page, per_page, **filters)
    
    @staticmethod
    def get_users_compact_list(include_deleted=False):
        """Get all users for compact list (without permissions)"""
        return UserService.get_users_compact_list(include_deleted=include_deleted)
    
    @staticmethod
    def search_users(id=None, username=None, role_id=None, environment_id=None):
        return UserService.search_users(id, username, role_id, environment_id)

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