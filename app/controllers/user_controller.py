# app/controllers/user_controller.py

from app.services.auth_service import AuthService
from app.services.user_service import UserService
# It's good practice to import specific models if type hinting is used,
# but since this controller is a pass-through, direct model usage is minimal.
# from app.models.user import User # Example if type hints were more complex

class UserController:
    """
    Controller for user-related operations.
    This class primarily delegates logic to the UserService and AuthService.
    """

    # The __init__ method is present but not strictly necessary for a class
    # composed entirely of static methods that don't use instance state.
    # It doesn't cause harm but could be removed if desired.
    def __init__(self):
        self.user_service = UserService() # This instance isn't used by the static methods

    @staticmethod
    def logout_user(token: str = None, username: str = None):
        """
        Handle user logout by attempting to blocklist the provided token.
        Delegates to AuthService.
        """
        return AuthService.logout_user(token=token, username=username)

    @staticmethod
    def create_user(first_name, last_name, email, contact_number, username, password, role_id, environment_id):
        """
        Create a new user.
        Delegates to UserService.
        """
        return UserService.create_user(first_name, last_name, email, contact_number, username, password, role_id, environment_id)

    @staticmethod
    def get_user(user_id: int):
        """
        Get a specific user by their ID.
        Delegates to UserService.
        """
        return UserService.get_user(user_id)

    @staticmethod
    def get_user_by_username(username: str):
        """
        Get a specific user by their username.
        Delegates to UserService.
        """
        return UserService.get_user_by_username(username)

    @staticmethod
    def get_all_users(include_deleted: bool = False):
        """
        Get all users, optionally including soft-deleted ones.
        This method typically applies environment-based restrictions for non-admins via the service layer.
        Delegates to UserService.
        """
        # UserService.get_all_users handles eager loading of relations.
        return UserService.get_all_users(include_deleted=include_deleted)

    @staticmethod
    def get_all_users_unrestricted(include_deleted: bool = False):
        """
        Get all users from all environments without standard environment restrictions.
        WARNING: Use with caution due to potential data exposure.
        Delegates to UserService.
        """
        return UserService.get_all_users_unrestricted(include_deleted=include_deleted)

    @staticmethod
    def get_batch(page: int = 1, per_page: int = 50, **filters):
        """
        Get a paginated batch of users with optional filters.
        Delegates to UserService.
        """
        return UserService.get_batch(page, per_page, **filters)

    @staticmethod
    def get_users_compact_list(include_deleted: bool = False):
        """
        Get a compact list of users, typically for dropdowns (e.g., ID, name).
        Delegates to UserService.
        """
        return UserService.get_users_compact_list(include_deleted=include_deleted)

    @staticmethod
    def search_users(id: int = None, username: str = None, role_id: int = None, environment_id: int = None):
        """
        Search for users based on provided criteria.
        Delegates to UserService.
        """
        return UserService.search_users(id, username, role_id, environment_id)

    @staticmethod
    def update_user(user_id: int, **kwargs):
        """
        Update an existing user's details.
        Delegates to UserService.
        """
        return UserService.update_user(user_id, **kwargs)

    @staticmethod
    def delete_user(user_id: int):
        """
        Soft delete a user.
        Delegates to UserService.
        """
        # The UserService.delete_user method handles the logic,
        # including what to do with related data (e.g., forms created by the user).
        return UserService.delete_user(user_id)

    @staticmethod
    def get_users_by_role(role_id: int):
        """
        Get all users assigned to a specific role.
        Delegates to UserService.
        """
        return UserService.get_users_by_role(role_id)

    @staticmethod
    def get_users_by_role_and_environment(role_id: int, environment_id: int):
        """
        Get all users assigned to a specific role within a specific environment.
        Delegates to UserService.
        """
        return UserService.get_users_by_role_and_environment(role_id, environment_id)

    @staticmethod
    def get_users_by_environment(environment_id: int):
        """
        Get all users belonging to a specific environment.
        Delegates to UserService.
        """
        return UserService.get_users_by_environment(environment_id)
