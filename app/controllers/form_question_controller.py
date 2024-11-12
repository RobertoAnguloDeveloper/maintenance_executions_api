# app/controllers/form_question_controller.py

from app.models.form_question import FormQuestion
from app.services.form_question_service import FormQuestionService
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class FormQuestionController:
    @staticmethod
    def create_form_question(form_id, question_id, order_number=None):
        """Create a new form question mapping"""
        return FormQuestionService.create_form_question(
            form_id=form_id,
            question_id=question_id,
            order_number=order_number
        )
        
    @staticmethod
    def get_all_form_questions(environment_id=None, include_relations=True):
        """
        Get all form questions with optional filtering
        
        Args:
            environment_id (int, optional): Filter by environment ID
            include_relations (bool): Whether to include related data
            
        Returns:
            list: List of FormQuestion objects or None if error occurs
        """
        try:
            return FormQuestionService.get_all_form_questions(
                environment_id=environment_id,
                include_relations=include_relations
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error in controller getting form questions: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in controller getting form questions: {str(e)}")
            return None

    @staticmethod
    def get_form_question(form_question_id):
        """Get a specific form question mapping"""
        return FormQuestionService.get_form_question(form_question_id)
    
    @staticmethod
    def get_form_question_detail(form_question_id: int) -> Optional[FormQuestion]:
        """
        Get detailed information for a specific form question
        
        Args:
            form_question_id (int): ID of the form question
            
        Returns:
            Optional[FormQuestion]: FormQuestion object or None if not found/error
        """
        try:
            return FormQuestionService.get_form_question_with_relations(form_question_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error in controller getting form question {form_question_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in controller getting form question {form_question_id}: {str(e)}")
            return None

    @staticmethod
    def get_questions_by_form(form_id):
        """Get all questions for a specific form"""
        return FormQuestionService.get_questions_by_form(form_id)

    @staticmethod
    def update_form_question(form_question_id, **kwargs):
        """Update a form question mapping"""
        return FormQuestionService.update_form_question(form_question_id, **kwargs)

    @staticmethod
    def delete_form_question(form_question_id):
        """Delete a form question mapping"""
        return FormQuestionService.delete_form_question(form_question_id)

    @staticmethod
    def bulk_create_form_questions(form_id, questions):
        """Bulk create form questions"""
        return FormQuestionService.bulk_create_form_questions(form_id, questions)