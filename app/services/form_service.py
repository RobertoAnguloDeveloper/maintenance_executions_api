# app/services/form_service.py

from datetime import datetime
from app.models.question import Question
from app.services.base_service import BaseService
from app.models.form import Form
from app.models.form_question import FormQuestion
from app import db
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

class FormService(BaseService):
    def __init__(self):
        super().__init__(Form)
        
    @staticmethod
    def get_all_forms(is_public=None):
        """
        Get all forms with optional public filter
        
        Args:
            is_public (bool, optional): Filter by public status
            
        Returns:
            list: List of Form objects
        """
        query = Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type),
            joinedload(Form.submissions)
        )
        
        if is_public is not None:
            query = query.filter_by(is_public=is_public)
            
        return query.order_by(Form.created_at.desc()).all()
    
    @staticmethod
    def get_form(form_id):
        """
        Get a form by ID with all its relationships loaded
        
        Args:
            form_id (int): ID of the form
            
        Returns:
            Form: Form object with loaded relationships or None if not found
        """
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type),
            joinedload(Form.submissions)
        ).get(form_id)

    def get_form_with_relations(self, form_id):
        """Get form with all related data loaded"""
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.form_questions).joinedload(FormQuestion.question)
        ).get(form_id)

    @staticmethod
    def get_forms_by_environment(environment_id):
        """Get forms by environment ID"""
        return (Form.query
                .join(Form.creator)
                .filter_by(environment_id=environment_id)
                .options(
                    joinedload(Form.creator),
                    joinedload(Form.form_questions)
                        .joinedload(FormQuestion.question)
                        .joinedload(Question.question_type),
                    joinedload(Form.submissions)
                )
                .order_by(Form.created_at.desc())
                .all())

    def get_forms_by_user_or_public(self, user_id, is_public=None):
        """Get forms created by user or public forms"""
        query = Form.query.filter(
            db.or_(
                Form.user_id == user_id,
                Form.is_public == True
            )
        )
        
        if is_public is not None:
            query = query.filter_by(is_public=is_public)
            
        return query.order_by(Form.created_at.desc()).all()
    
    @staticmethod
    def get_public_forms():
        """
        Get all public forms with related data loaded
        
        Returns:
            list: List of Form objects that are public
        """
        return (Form.query
                .filter_by(is_public=True)
                .options(
                    joinedload(Form.creator),
                    joinedload(Form.form_questions)
                        .joinedload(FormQuestion.question)
                        .joinedload(Question.question_type),
                    joinedload(Form.submissions)
                )
                .order_by(Form.created_at.desc())
                .all())
    
    @staticmethod
    def get_forms_by_creator(username):
        """
        Get all forms created by a specific user
        
        Args:
            username (str): Username of the creator
            
        Returns:
            list: List of Form objects or None if user not found
        """
        from app.models.user import User  # Import here to avoid circular imports
        
        # First verify user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            return None
            
        return (Form.query
                .filter_by(user_id=user.id)
                .options(
                    joinedload(Form.creator),
                    joinedload(Form.form_questions)
                        .joinedload(FormQuestion.question)
                        .joinedload(Question.question_type),
                    joinedload(Form.submissions)
                )
                .order_by(Form.created_at.desc())
                .all())

    def create_form_with_questions(self, title, description, user_id, questions, is_public=False):
        """Create a new form with questions"""
        try:
            form = Form(
                title=title,
                description=description,
                user_id=user_id,
                is_public=is_public
            )
            db.session.add(form)
            
            # Add questions with order
            for question in questions:
                form_question = FormQuestion(
                    form=form,
                    question_id=question['question_id'],
                    order_number=question.get('order_number')
                )
                db.session.add(form_question)
            
            db.session.commit()
            return form, None
        except IntegrityError:
            db.session.rollback()
            return None, "Invalid user_id or question_id provided"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    @staticmethod
    def update_form(form_id, **kwargs):
        """
        Update a form's details
        
        Args:
            form_id (int): ID of the form to update
            **kwargs: Fields to update (title, description, is_public, user_id)
            
        Returns:
            tuple: (Updated Form object, error message or None)
        """
        try:
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"
                
            for key, value in kwargs.items():
                if hasattr(form, key):
                    setattr(form, key, value)
            
            form.updated_at = datetime.utcnow()
            db.session.commit()
            return form, None
            
        except IntegrityError:
            db.session.rollback()
            return None, "Database integrity error. Please check if the user_id is valid."
        except Exception as e:
            db.session.rollback()
            return None, str(e)