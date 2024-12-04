from typing import Optional
from app import db
from app.controllers.form_controller import FormController
from app.controllers.user_controller import UserController
from app.models import Environment
from datetime import datetime
from app.models.answers_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
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
    def get_environment(environment_id: int) -> Optional[Environment]:
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
            query = Environment.query.options(
                joinedload(Environment.users)   # Assuming there's a forms relationship
            )
            
            if not include_deleted:
                query = query.filter(Environment.is_deleted == False)
                
            return query.order_by(Environment.id).all()
        except Exception as e:
            logger.error(f"Database error getting environments: {str(e)}", exc_info=True)
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
    def delete_environment(environment_id: int) -> tuple[bool, Optional[str]]:
        """
        Delete an environment and all associated data through cascade soft delete
        
        Args:
            environment_id (int): ID of the environment to delete
            
        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        try:
            environment = Environment.query.filter_by(
                id=environment_id,
                is_deleted=False
            ).first()
            
            if not environment:
                return False, "Environment not found"

            # Start transaction
            db.session.begin_nested()

            # 1. Soft delete users in this environment
            users = User.query.filter_by(
                environment_id=environment_id,
                is_deleted=False
            ).all()
            
            for user in users:
                user.soft_delete()
                
                # 2. Soft delete forms created by these users
                forms = Form.query.filter_by(
                    user_id=user.id,
                    is_deleted=False
                ).all()
                
                for form in forms:
                    form.soft_delete()
                    
                    # 3. Soft delete form questions
                    FormQuestion.query.filter_by(
                        form_id=form.id,
                        is_deleted=False
                    ).update({
                        'is_deleted': True,
                        'deleted_at': datetime.utcnow()
                    })
                    
                    # 4. Soft delete form submissions
                    submissions = FormSubmission.query.filter_by(
                        form_id=form.id,
                        is_deleted=False
                    ).all()
                    
                    for submission in submissions:
                        submission.soft_delete()
                        
                        # 5. Soft delete attachments
                        Attachment.query.filter_by(
                            form_submission_id=submission.id,
                            is_deleted=False
                        ).update({
                            'is_deleted': True,
                            'deleted_at': datetime.utcnow()
                        })
                        
                        # 6. Soft delete submitted answers
                        AnswerSubmitted.query.filter_by(
                            form_submission_id=submission.id,
                            is_deleted=False
                        ).update({
                            'is_deleted': True,
                            'deleted_at': datetime.utcnow()
                        })

            # Finally soft delete the environment itself
            environment.soft_delete()
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Environment {environment_id} and all associated data soft deleted")
            return True, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting environment: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def get_users_in_environment(environment_id: int) -> list[User]:
        """Get all non-deleted users in an environment"""
        try:
            return User.query.filter_by(
                environment_id=environment_id,
                is_deleted=False
            ).all()
        except Exception as e:
            logger.error(f"Error getting users in environment {environment_id}: {str(e)}")
            return []

    @staticmethod
    def get_forms_in_environment(environment_id: int) -> list[Form]:
        """Get all non-deleted forms in an environment"""
        try:
            return (Form.query
                .join(User)
                .filter(
                    User.environment_id == environment_id,
                    Form.is_deleted == False,
                    User.is_deleted == False
                )
                .all())
        except Exception as e:
            logger.error(f"Error getting forms in environment {environment_id}: {str(e)}")
            return []