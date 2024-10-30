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
    def get_all_environments():
        return EnvironmentService.get_all_environments()

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