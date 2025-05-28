# app/services/user_service.py

from typing import Optional, Union, List
from app import db
from app.models.answer_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.environment import Environment
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.role import Role
from app.models.user import User
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.services.base_service import BaseService
import logging
from app.utils.helpers import validate_email


logger = logging.getLogger(__name__)

class UserService(BaseService):
    def __init__(self):
        super().__init__(User)

    @staticmethod
    def create_user(first_name, last_name, email, contact_number, username, password, role_id, environment_id):
        try:
            if not validate_email(email):
                return None, "Please enter a valid email address (e.g., user@domain.com)."

            if User.query.filter_by(username=username).first():
                return None, "Username already exists."
            
            if User.query.filter_by(email=email).first():
                 return None, "Email address already in use."

            role = Role.query.filter_by(id=role_id, is_deleted=False).first()
            if not role:
                return None, f"Role with ID {role_id} not found or is deleted."
            
            environment = Environment.query.filter_by(id=environment_id, is_deleted=False).first()
            if not environment:
                return None, f"Environment with ID {environment_id} not found or is deleted."

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
            error_message = str(e.orig).lower() # type: ignore
            if "users_username_key" in error_message or ("unique constraint" in error_message and "username" in error_message):
                return None, "Username already exists."
            elif "users_email_key" in error_message or ("unique constraint" in error_message and "email" in error_message): 
                return None, "Email address already in use."
            else:
                logger.error(f"Unhandled IntegrityError during user creation: {e.orig}", exc_info=True) # type: ignore
                return None, "A database integrity error occurred. Please check your input."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            return None, str(e)

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """Get non-deleted user by ID, eager loading role and environment."""
        return User.query.options(
            joinedload(User.role),
            joinedload(User.environment)
        ).filter_by(id=user_id, is_deleted=False).first()

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get non-deleted user by username, eager loading role and environment."""
        return User.query.options(
            joinedload(User.role),
            joinedload(User.environment)
        ).filter_by(username=username, is_deleted=False).first()

    @staticmethod
    def get_all_users(include_deleted: bool = False) -> List[User]:
        """Get all users with optional inclusion of deleted records, eager loading relations."""
        try:
            query = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            )
            if not include_deleted:
                query = query.filter(User.is_deleted == False)
            return query.order_by(User.id).all()
        except Exception as e:
            logger.error(f"Database error getting all users: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_all_users_unrestricted(include_deleted: bool = False) -> List[User]:
        """
        Get all users from all environments, optionally including deleted ones.
        This method bypasses standard environment-based access controls.
        Eager loads role and environment.
        """
        try:
            query = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            )
            if not include_deleted:
                query = query.filter(User.is_deleted == False)
            return query.order_by(User.id).all()
        except Exception as e:
            logger.error(f"Database error getting all unrestricted users: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of users with pagination directly from database.
        Eager loads role and environment for serialization.
        """
        try:
            offset = (page - 1) * per_page if page > 0 and per_page > 0 else 0
            query = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            )

            include_deleted = filters.get('include_deleted', False)
            if not include_deleted:
                query = query.filter(User.is_deleted == False)

            role_id = filters.get('role_id')
            if role_id is not None:
                query = query.filter(User.role_id == role_id)

            environment_id = filters.get('environment_id')
            if environment_id is not None:
                query = query.filter(User.environment_id == environment_id)

            total_count = query.count()
            users = query.order_by(User.id).offset(offset).limit(per_page).all()
            
            users_data = [
                user.to_dict(
                    include_details=True, 
                    include_deleted=include_deleted
                ) for user in users
            ]
            return total_count, users_data
        except Exception as e:
            logger.error(f"Error in user batch pagination service: {str(e)}", exc_info=True)
            return 0, []

    @staticmethod
    def get_users_compact_list(include_deleted: bool = False) -> List[User]:
        """Get all users for compact list view (without permissions), eager loading relations."""
        try:
            query = User.query.options(
                joinedload(User.role),
                joinedload(User.environment)
            )
            if not include_deleted:
                query = query.filter(User.is_deleted == False)
            return query.order_by(User.username).all()
        except Exception as e:
            logger.error(f"Database error getting compact users list: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_all_users_with_relations(include_deleted: bool = False) -> List[User]:
        """Alias for get_all_users for clarity if used elsewhere with this name."""
        return UserService.get_all_users(include_deleted=include_deleted)

    @staticmethod
    def search_users(id=None, username=None, role_id=None, environment_id=None) -> list[User]:
        """Search non-deleted users with filters, eager loading relations."""
        query = User.query.options(
            joinedload(User.role),
            joinedload(User.environment)
        ).filter_by(is_deleted=False)

        if id is not None:
            query = query.filter(User.id == id)
        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))
        if role_id is not None:
            query = query.filter(User.role_id == role_id)
        if environment_id is not None:
            query = query.filter(User.environment_id == environment_id)

        return query.order_by(User.username).all()

    @staticmethod
    def update_user(user_id, **kwargs):
        user = User.query.get(user_id) 
        if not user or user.is_deleted:
            return None, "User not found or has been deleted."

        changed_fields = False

        for key, value in kwargs.items():
            if hasattr(user, key):
                current_value = getattr(user, key)
                if key == 'password':
                    if value: 
                        user.set_password(value)
                        changed_fields = True
                elif key == 'email':
                    if value != current_value:
                        if not validate_email(value):
                            return None, "Please enter a valid email address (e.g., user@domain.com)."
                        existing_user_with_email = User.query.filter(User.email == value, User.id != user_id, User.is_deleted == False).first()
                        if existing_user_with_email:
                            return None, "Email address already in use by another user."
                        setattr(user, key, value)
                        changed_fields = True
                elif key == 'username':
                    if value != current_value:
                        existing_user_with_username = User.query.filter(User.username == value, User.id != user_id, User.is_deleted == False).first()
                        if existing_user_with_username:
                            return None, "Username already exists."
                        setattr(user, key, value)
                        changed_fields = True
                elif key == 'environment_id':
                    if value != current_value:
                        if value is not None:
                            env = Environment.query.filter_by(id=value, is_deleted=False).first()
                            if not env:
                                return None, f"Environment with ID {value} not found or is deleted."
                        setattr(user, key, value)
                        changed_fields = True
                elif key == 'role_id':
                     if value != current_value:
                        if value is not None:
                            role = Role.query.filter_by(id=value, is_deleted=False).first()
                            if not role:
                                return None, f"Role with ID {value} not found or is deleted."
                        setattr(user, key, value)
                        changed_fields = True
                else:
                    if value != current_value:
                        setattr(user, key, value)
                        changed_fields = True
            else:
                logger.warning(f"Attempted to update non-existent attribute '{key}' on User ID {user_id}.")


        if not changed_fields:
            return user, "No changes detected."

        try:
            user.updated_at = datetime.utcnow() 
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig).lower() # type: ignore
            if "users_username_key" in error_message or ("unique constraint" in error_message and "username" in error_message):
                return None, "Error: Username already exists."
            elif "users_email_key" in error_message or ("unique constraint" in error_message and "email" in error_message):
                return None, "Error: Email already exists."
            else:
                logger.error(f"Unhandled IntegrityError during user update for ID {user_id}: {e.orig}", exc_info=True) # type: ignore
                return None, "Database integrity error during update."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Generic error during user update for ID {user_id}: {e}", exc_info=True)
            return None, f"Error: {str(e)}"

        return user, None

    @staticmethod
    def get_users_by_role(role_id: int) -> list[User]:
        """Get all non-deleted users with a specific role, eager loading relations."""
        return User.query.options(
            joinedload(User.role),
            joinedload(User.environment)
        ).filter_by(role_id=role_id, is_deleted=False).order_by(User.username).all()

    @staticmethod
    def get_users_by_role_and_environment(role_id: int, environment_id: int) -> list[User]:
        """Get non-deleted users by specific role and environment, eager loading relations."""
        try:
            return (User.query
                .options(
                    joinedload(User.role),
                    joinedload(User.environment)
                )
                .join(Role, Role.id == User.role_id) 
                .join(Environment, Environment.id == User.environment_id) 
                .filter(
                    User.role_id == role_id,
                    User.environment_id == environment_id,
                    User.is_deleted == False,
                    Role.is_deleted == False, 
                    Environment.is_deleted == False 
                )
                .order_by(User.username)
                .all())
        except Exception as e:
            logger.error(f"Error getting users by role {role_id} and environment {environment_id}: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_users_by_environment(environment_id: int) -> list[User]:
        """Get all non-deleted users in an environment, eager loading relations."""
        return User.query.options(
            joinedload(User.role),
            joinedload(User.environment)
        ).filter_by(environment_id=environment_id, is_deleted=False).order_by(User.username).all()

    @staticmethod
    def delete_user(user_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Soft delete a user and handle basic related data.
        """
        try:
            user = User.query.filter_by(id=user_id, is_deleted=False).first()
            if not user:
                return False, "User not found or already deleted."

            db.session.begin_nested() 

            deletion_stats = {
                'user_id': user.id,
                'username': user.username,
                'forms_marked_for_review': 0, 
            }
            
            user_forms = Form.query.filter_by(user_id=user.id, is_deleted=False).all()
            for form in user_forms:
                # For a full cascade, you would call FormService.delete_form here
                # which would handle its own related entities.
                # This example just counts them for the stats.
                deletion_stats['forms_marked_for_review'] += 1
                # form.soft_delete() # If you want to soft-delete forms directly here

            user.soft_delete()
            db.session.commit()

            logger.info(f"User {user_id} ('{user.username}') soft-deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting user {user_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
