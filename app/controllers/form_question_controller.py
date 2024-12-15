# app/controllers/form_question_controller.py

from flask_jwt_extended import get_jwt_identity
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.services.auth_service import AuthService
from app.services.form_question_service import FormQuestionService
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional, Tuple, Union
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
    def get_all_form_questions(include_relations=True):
        """Get all form questions with proper environment filtering"""
        try:
            questions = FormQuestionService.get_all_form_questions(
                include_relations=include_relations
            )
            
            if questions is None:
                return []
                
            # Convert to dictionary representation
            questions_data = []
            for question in questions:
                try:
                    question_dict = question.to_dict()
                    questions_data.append(question_dict)
                except Exception as e:
                    logger.error(f"Error converting question {question.id} to dict: {str(e)}")
                    continue
                    
            return questions_data
            
        except Exception as e:
            logger.error(f"Error in get_all_form_questions controller: {str(e)}")
            return []

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
    def get_questions_by_form(form_id: int) -> List[Dict]:
        """
        Get all questions for a specific form with form info shown once
        
        Args:
            form_id: ID of the form
                
        Returns:
            List of dictionaries containing form questions
        """
        try:
            form, questions = FormQuestionService.get_questions_by_form(form_id)
            
            if not form:
                return []
                
            result = []
            
            # Create basic form info once
            form_info = {
                "id": form.id,
                "title": form.title,
                "description": form.description,
                "creator": {
                    "id": form.creator.id,
                    "username": form.creator.username,
                    "environment_id": form.creator.environment_id
                } if form.creator else None
            }
            
            # Add questions with minimal form info
            for question in questions:
                question_dict = {
                    'id': question.id,
                    'question_id': question.question.id if question.question else None,
                    'order_number': question.order_number,
                    'question': {
                        'text': question.question.text,
                        'type': question.question.question_type.type,
                        'remarks': question.question.remarks
                    } if question.question else None
                }
                
                # Add form info only to first question
                if not result:
                    question_dict['form'] = form_info
                    
                result.append(question_dict)
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting form questions: {str(e)}")
            return []

    @staticmethod
    def update_form_question(form_question_id, **kwargs):
        """Update a form question mapping"""
        return FormQuestionService.update_form_question(form_question_id, **kwargs)

    @staticmethod
    def delete_form_question(form_question_id: int) -> Tuple[bool, Union[Dict[str, int], str]]:
        """
        Delete a form question with cascade validation
        
        Args:
            form_question_id: ID of the form question to delete
            
        Returns:
            tuple: (Success boolean, Dict with deletion stats or error message)
        """
        try:
            return FormQuestionService.delete_form_question(form_question_id)
        except Exception as e:
            logger.error(f"Error in delete_form_question controller: {str(e)}")
            return False, str(e)

    @staticmethod
    def bulk_create_form_questions(form_id, questions):
        """
        Bulk create form questions
        
        Args:
            form_id (int): Form ID
            questions (list): List of question data
                
        Returns:
            tuple: (List of created FormQuestion objects, error message)
        """
        try:
            # Validate form exists
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"

            # Create form questions
            form_questions, error = FormQuestionService.bulk_create_form_questions(form_id, questions)
            
            if error:
                return None, error
                
            return form_questions, None

        except Exception as e:
            logger.error(f"Error in bulk_create_form_questions controller: {str(e)}")
            return None, str(e)