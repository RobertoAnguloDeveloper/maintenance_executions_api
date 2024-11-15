# app/services/form_question_service.py

from typing import Optional
from app import db
from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app.models.question import Question
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class FormQuestionService:
    @staticmethod
    def create_form_question(form_id, question_id, order_number=None):
        """
        Create a new form question mapping
        
        Args:
            form_id (int): ID of the form
            question_id (int): ID of the question
            order_number (int, optional): Order number for the question
            
        Returns:
            tuple: (FormQuestion, str) - Created form question or error message
        """
        try:
            # Validate form exists
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"

            # Validate question exists
            question = Question.query.get(question_id)
            if not question:
                return None, "Question not found"

            # If no order number provided, get the next available one
            if order_number is None:
                max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                    .filter_by(form_id=form_id).scalar()
                order_number = (max_order or 0) + 1

            form_question = FormQuestion(
                form_id=form_id,
                question_id=question_id,
                order_number=order_number
            )
            
            db.session.add(form_question)
            db.session.commit()
            
            # Refresh to load relationships
            db.session.refresh(form_question)
            
            return form_question, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_id or question_id"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form question: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_all_form_questions(environment_id=None, include_relations=True, include_deleted=False):
        """Get all form questions with filters"""
        query = FormQuestion.query

        if not include_deleted:
            query = query.filter(FormQuestion.is_deleted == False)

        if environment_id:
            query = query.join(
                Form,
                FormQuestion.form_id == Form.id
            ).join(
                User,
                Form.user_id == User.id
            ).filter(
                User.environment_id == environment_id
            )

        return query.order_by(
            FormQuestion.form_id,
            FormQuestion.order_number.nullslast()
        ).all()
        
    @staticmethod
    def get_form_question_with_relations(form_question_id: int) -> Optional[FormQuestion]:
        """
        Get a specific form question with all its relationships loaded
        
        Args:
            form_question_id (int): ID of the form question to retrieve
            
        Returns:
            Optional[FormQuestion]: FormQuestion object with relationships or None if not found
            
        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            return FormQuestion.query.options(
                joinedload(FormQuestion.form),
                joinedload(FormQuestion.question).joinedload(Question.question_type),
                joinedload(FormQuestion.form_answers).joinedload(FormAnswer.answer)
            ).get(form_question_id)
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting form question {form_question_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting form question {form_question_id}: {str(e)}")
            raise

    @staticmethod
    def get_form_question(form_question_id):
        """Get a specific form question mapping"""
        return FormQuestion.query.get(form_question_id)

    @staticmethod
    def get_questions_by_form(form_id):
        """Get all questions for a specific form"""
        return FormQuestion.query\
            .filter_by(form_id=form_id)\
            .order_by(FormQuestion.order_number)\
            .all()

    @staticmethod
    def update_form_question(form_question_id, **kwargs):
        """Update a form question mapping"""
        try:
            form_question = FormQuestion.query.get(form_question_id)
            if not form_question:
                return None, "Form question not found"

            # Update fields
            for key, value in kwargs.items():
                if hasattr(form_question, key):
                    setattr(form_question, key, value)

            form_question.updated_at = datetime.utcnow()
            db.session.commit()
            return form_question, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid question_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_form_question(form_question_id):
        """Soft delete a form question"""
        try:
            form_question = FormQuestion.query.get(form_question_id)
            if not form_question:
                return False, "Form question not found"

            form_question.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def bulk_create_form_questions(form_id, questions):
        """
        Bulk create form questions
        
        Args:
            form_id (int): ID of the form
            questions (list): List of dicts with question_id and optional order_number
            
        Returns:
            tuple: (List[FormQuestion], str) - List of created questions or error message
        """
        try:
            # First verify the form exists
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"

            # Get current max order
            current_max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                .filter_by(form_id=form_id).scalar() or 0

            form_questions = []
            
            # Create and add each form question individually
            for i, question_data in enumerate(questions, 1):
                question_id = question_data.get('question_id')
                
                # Verify question exists
                if not Question.query.get(question_id):
                    return None, f"Question with ID {question_id} not found"

                # Create form question
                form_question = FormQuestion(
                    form_id=form_id,
                    question_id=question_id,
                    order_number=question_data.get('order_number', current_max_order + i)
                )
                
                # Add to session
                db.session.add(form_question)
                form_questions.append(form_question)

            # Commit the transaction
            db.session.commit()

            # Query to get the persisted form questions with relationships loaded
            persisted_questions = FormQuestion.query.options(
                joinedload(FormQuestion.form),
                joinedload(FormQuestion.question)
            ).filter(
                FormQuestion.id.in_([fq.id for fq in form_questions])
            ).all()

            return persisted_questions, None

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error in bulk_create_form_questions: {str(e)}")
            return None, "Invalid form_id or question_id provided"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk_create_form_questions: {str(e)}")
            return None, str(e)