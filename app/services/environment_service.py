from app import db
from app.models import Environment
from datetime import datetime
from app.services.base_service import BaseService
from sqlalchemy.exc import IntegrityError

class EnvironmentService(BaseService):
    def __init__(self):
        super().__init__(Environment)
    
    @staticmethod
    def create_environment(name, description):
        try:
            new_environment = Environment(
                name=name, 
                description=description
            )
            db.session.add(new_environment)
            db.session.commit()
            return new_environment, None
        except IntegrityError:
            db.session.rollback()
            return None, "An environment with this name already exists"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_environment(environment_id):
        return Environment.query.get(environment_id)

    @staticmethod
    def get_environment_by_name(name):
        return Environment.get_by_name(name)

    @staticmethod
    def get_all_environments():
        return Environment.query.order_by(Environment.id).all()

    @staticmethod
    def update_environment(environment_id, **kwargs):
        environment = Environment.query.get(environment_id)
        if environment:
            for key, value in kwargs.items():
                if hasattr(environment, key):
                    setattr(environment, key, value)
            try:
                db.session.commit()
                return environment, None
            except IntegrityError:
                db.session.rollback()
                return None, "An environment with this name already exists"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Environment not found"

    @staticmethod
    def delete_environment(environment_id):
        environment = Environment.query.get(environment_id)
        if environment:
            try:
                db.session.delete(environment)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Environment not found"

    @staticmethod
    def get_users_in_environment(environment_id):
        environment = Environment.query.get(environment_id)
        if environment:
            return environment.users.all()
        return []

    @staticmethod
    def get_forms_in_environment(environment_id):
        environment = Environment.query.get(environment_id)
        if environment:
            return environment.forms.all()
        return []