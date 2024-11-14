from app import db
from app.models.user import User
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.services.base_service import BaseService
import logging

logger = logging.getLogger(__name__)

class UserService(BaseService):
    def __init__(self):
        super().__init__(User)
        
    @staticmethod
    def create_user(first_name, last_name, email, contact_number, username, password, role_id, environment_id):
        try:
            new_user = User(
                first_name=first_name, 
                last_name=last_name, 
                email=email,
                contact_number=contact_number,
                username=username, 
                role_id=role_id, 
                environment_id=environment_id
                
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            return new_user, None
        except IntegrityError as e:
            db.session.rollback()
            if "username" in str(e.orig):
                return None, "Username already exists"
            elif "email" in str(e.orig):
                return None, "Email already exists"
            else:
                return None, str(e)
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_user(user_id):
        return User.query.filter_by(id=user_id, is_deleted=False).first()

    @staticmethod
    def get_user_by_username(username):
        return User.query.filter_by(username=username, is_deleted=False).first()

    @staticmethod
    def get_all_users(include_deleted=False):
        """Get all users with optional inclusion of deleted records"""
        try:
            query = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            )
            
            if not include_deleted:
                query = query.filter(User.is_deleted == False)
                
            return query.order_by(User.id).all()
        except Exception as e:
            logger.error(f"Database error getting users: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_all_users_with_relations(include_deleted=False):
        try:
            query = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            )
            if not include_deleted:
                query = query.filter(User.is_deleted == False)
            users = query.order_by(User.id).all()
            return users
        except Exception as e:
            logger.error(f"Database error getting users: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def search_users(username=None, role_id=None, environment_id=None):
        """Search users with filters, excluding soft deleted"""
        query = User.query.filter_by(is_deleted=False)
        
        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))
        if role_id:
            query = query.filter_by(role_id=role_id)
        if environment_id:
            query = query.filter_by(environment_id=environment_id)
            
        return query.all()

    @staticmethod
    def update_user(user_id, **kwargs):
        user = User.query.get(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    if key == 'password':
                        user.set_password(value)
                    else:
                        setattr(user, key, value)
            
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return None, "Error: Username or email already exists"
            except Exception as e:
                db.session.rollback()
                return None, f"Error: {str(e)}"
            
            return user, None
        return None, "User not found"
    
    @staticmethod
    def get_users_by_role(role_id):
        return User.query.filter_by(role_id=role_id, is_deleted=False).all()
    
    @staticmethod
    def get_users_by_role_and_environment(role_id, environment_id):
        try:
            return User.query.filter(
                User.role_id == role_id,
                User.environment_id == environment_id,
                User.is_deleted == False  # Add soft delete filter
            ).all()
        except Exception as e:
            logger.error(f"Error getting users by role and environment: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_users_by_environment(environment_id):
        """Get all non-deleted users in an environment"""
        return User.query.filter_by(
            environment_id=environment_id, 
            is_deleted=False
        ).all()

    @staticmethod
    def delete_user(user_id):
        user = User.query.get(user_id)
        if user:
            user.soft_delete()
            db.session.commit()
            return True
        return False