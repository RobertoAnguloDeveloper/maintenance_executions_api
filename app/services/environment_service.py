from app import db
from app.controllers.form_controller import FormController
from app.controllers.user_controller import UserController
from app.models import Environment
from datetime import datetime
from app.models.form import Form
from app.models.user import User
from app.services.base_service import BaseService
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

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
        """Get non-deleted environment by ID"""
        return Environment.query.filter_by(
            id=environment_id, 
            is_deleted=False
        ).first()

    @staticmethod
    def get_environment_by_name(name):
        """Get non-deleted environment by name"""
        return Environment.query.filter_by(
            name=name, 
            is_deleted=False
        ).first()

    @staticmethod
    def get_all_environments(include_deleted=False):
        """Get all environments with optional inclusion of deleted records"""
        try:
            query = Environment.query
            if not include_deleted:
                query = query.filter(Environment.is_deleted == False)
            return query.order_by(Environment.id).all()
        except Exception as e:
            logger.error(f"Error getting environments: {str(e)}")
            raise

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
                environment.soft_delete()
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Environment not found"

    @staticmethod
    def get_users_in_environment(environment_id: int):
        """
        Get all non-deleted users in an environment with their relationships loaded
        
        Args:
            environment_id (int): ID of the environment
            
        Returns:
            list: List of User objects or empty list
        """
        try:
            users = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            ).filter(
                User.environment_id == environment_id,
                User.is_deleted == False  # Add soft delete filter
            ).order_by(User.username).all()
            
            return users or []
            
        except Exception as e:
            logger.error(f"Error getting users in environment {environment_id}: {str(e)}")
            return []

    @staticmethod
    def get_forms_in_environment(environment_id: int):
        """
        Get all non-deleted forms in an environment using a single optimized query
        
        Args:
            environment_id (int): ID of the environment
            
        Returns:
            list: List of Form objects or empty list
        """
        try:
            # Single query to get all forms related to users in the environment
            forms = Form.query.options(
                joinedload(Form.creator).joinedload(User.environment),
                joinedload(Form.form_questions)
            ).join(
                User, Form.user_id == User.id
            ).filter(
                User.environment_id == environment_id,
                Form.is_deleted == False,    # Add soft delete filter for forms
                User.is_deleted == False     # Add soft delete filter for users
            ).order_by(
                Form.created_at.desc()
            ).all()
            
            return forms or []
            
        except Exception as e:
            logger.error(f"Error getting forms in environment {environment_id}: {str(e)}")
            return []