from app.services.environment_service import EnvironmentService

class EnvironmentController:
    @staticmethod
    def create_environment(name, description):
        environment, error = EnvironmentService.create_environment(name, description)
        if error:
            return None, error
        return environment, None

    @staticmethod
    def get_environment(environment_id):
        return EnvironmentService.get_environment(environment_id)

    @staticmethod
    def get_environment_by_name(name):
        return EnvironmentService.get_environment_by_name(name)

    @staticmethod
    def get_all_environments(include_deleted=False):
        """Get all environments with optional inclusion of deleted records"""
        return EnvironmentService.get_all_environments(include_deleted=include_deleted)
    
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of environments with pagination
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, environments)
        """
        return EnvironmentService.get_batch(page, per_page, **filters)

    @staticmethod
    def update_environment(environment_id, **kwargs):
        return EnvironmentService.update_environment(environment_id, **kwargs)

    @staticmethod
    def delete_environment(environment_id):
        return EnvironmentService.delete_environment(environment_id)

    @staticmethod
    def get_users_in_environment(environment_id):
        return EnvironmentService.get_users_in_environment(environment_id)

    @staticmethod
    def get_forms_in_environment(environment_id):
        return EnvironmentService.get_forms_in_environment(environment_id)