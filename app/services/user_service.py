from typing import Optional, Union
from app import db
from app.models.answers_submitted import AnswerSubmitted
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
            # Verificar existencia antes de crear
            if User.query.filter_by(username=username).first():
                db.session.rollback()
                return None, "Username already exists"
            if not validate_email(email):
                db.session.rollback()
                return None, "Please enter a valid email address (e.g., user@domain.com)"
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
                db.session.rollback()
                return None, "Username already exists"
            else:
                return None, str(e)
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """Get non-deleted user by ID"""
        return User.query.filter_by(
            id=user_id,
            is_deleted=False
        ).first()

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
    def search_users(id=None, username=None, role_id=None, environment_id=None) -> list[User]:
        """Search non-deleted users with filters"""
        query = User.query.filter_by(is_deleted=False)
        
        if id:
            query = User.query.filter_by(id=id)
        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))
        if role_id:
            query = query.filter_by(role_id=role_id)
        if environment_id:
            query = query.filter_by(environment_id=environment_id)
            
        return query.order_by(User.username).all()

    @staticmethod
    def update_user(user_id, **kwargs):
        user = User.query.get(user_id)
        print(kwargs.items())
        if user:
            for key, value in kwargs.items():      
                if key == 'password':
                    user.set_password(value)
                elif key == 'email':
                    if not validate_email(value):
                        return None, "Please enter a valid email address (e.g., user@domain.com)"
                    setattr(user, key, value)
                if key == 'environment_id':
                    if Environment.query.filter_by(id=value, is_deleted=False).first():
                        setattr(user, key, value)
                    else:
                        return None, "Environment not found"
                elif key == 'role_id':
                    if Role.query.filter_by(id=value, is_deleted=False).first():
                        setattr(user, key, value)
                else:
                    setattr(user, key, value)
            
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return None, "Error: Username already exists"
            except Exception as e:
                db.session.rollback()
                return None, f"Error: {str(e)}"
            
            return user, None
        return None, "User not found"
    
    @staticmethod
    def get_users_by_role(role_id: int) -> list[User]:
        """Get all non-deleted users with a specific role"""
        return User.query.filter_by(
            role_id=role_id,
            is_deleted=False
        ).order_by(User.username).all()
    
    @staticmethod
    def get_users_by_role_and_environment(role_id, environment_id):
        try:
            return (User.query
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
            logger.error(f"Error getting users by role and environment: {str(e)}")
            return []

    @staticmethod
    def get_users_by_environment(environment_id: int) -> list[User]:
        """Get all non-deleted users in an environment"""
        return User.query.filter_by(
            environment_id=environment_id,
            is_deleted=False
        ).order_by(User.username).all()

    @staticmethod
    def delete_user(user_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a user and all associated data through cascade soft delete
        
        Args:
            user_id (int): ID of the user to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            user = User.query.filter_by(
                id=user_id,
                is_deleted=False
            ).first()
            
            if not user:
                return False, "User not found"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'forms': 0,
                'form_questions': 0,
                'form_submissions': 0,
                'attachments': 0,
                'answers_submitted': 0
            }

            # 1. Soft delete forms created by user
            forms = Form.query.filter_by(
                user_id=user_id,
                is_deleted=False
            ).all()

            for form in forms:
                # Soft delete the form
                form.soft_delete()
                deletion_stats['forms'] += 1

                # 2. Soft delete form questions
                form_questions = FormQuestion.query.filter_by(
                    form_id=form.id,
                    is_deleted=False
                ).all()
                
                for fq in form_questions:
                    fq.soft_delete()
                    deletion_stats['form_questions'] += 1

                # 3. Soft delete form submissions and related data
                submissions = FormSubmission.query.filter_by(
                    form_id=form.id,
                    is_deleted=False
                ).all()

                for submission in submissions:
                    # Soft delete submission
                    submission.soft_delete()
                    deletion_stats['form_submissions'] += 1

                    # 4. Soft delete attachments
                    attachments = Attachment.query.filter_by(
                        form_submission_id=submission.id,
                        is_deleted=False
                    ).all()
                    
                    for attachment in attachments:
                        attachment.soft_delete()
                        deletion_stats['attachments'] += 1

                    # 5. Soft delete submitted answers
                    answers_submitted = AnswerSubmitted.query.filter_by(
                        form_submissions_id=submission.id,
                        is_deleted=False
                    ).all()
                    
                    for answer in answers_submitted:
                        answer.soft_delete()
                        deletion_stats['answers_submitted'] += 1

            # 6. Soft delete submissions made by this user
            user_submissions = FormSubmission.query.filter_by(
                submitted_by=user.username,
                is_deleted=False
            ).all()

            for submission in user_submissions:
                if not submission.is_deleted:  # Check if not already deleted from form deletion
                    submission.soft_delete()
                    deletion_stats['form_submissions'] += 1

                    # Soft delete related attachments and answers if not already deleted
                    for attachment in submission.attachments:
                        if not attachment.is_deleted:
                            attachment.soft_delete()
                            deletion_stats['attachments'] += 1

                    for answer in submission.answers_submitted:
                        if not answer.is_deleted:
                            answer.soft_delete()
                            deletion_stats['answers_submitted'] += 1

            # Finally soft delete the user
            user.soft_delete()

            # Commit all changes
            db.session.commit()
            
            logger.info(f"User {user_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting user: {str(e)}"
            logger.error(error_msg)
            return False, error_msg