# app/controllers/form_answer_controller.py

from typing import Dict, Tuple, Union
from app.models.user import User
from app.services.form_answer_service import FormAnswerService
import logging

logger = logging.getLogger(__name__)

class FormAnswerController:
    @staticmethod
    def create_form_answer(form_question_id: int, answer_id: int) -> tuple:
        """
        Create a new form answer
        
        Args:
            form_question_id (int): ID of the form question
            answer_id (int): ID of the answer
            
        Returns:
            tuple: (FormAnswer, str) Created form answer or error message
        """
        return FormAnswerService.create_form_answer(
            form_question_id=form_question_id,
            answer_id=answer_id
        )

    @staticmethod
    def bulk_create_form_answers(form_answers_data):
        """Bulk create form answers"""
        return FormAnswerService.bulk_create_form_answers(form_answers_data)
    
    @staticmethod
    def get_all_form_answers():
        """Get a specific form answer"""
        return FormAnswerService.get_all_form_answers()

    @staticmethod
    def get_form_answer(form_answer_id):
        """Get a specific form answer"""
        return FormAnswerService.get_form_answer(form_answer_id)

    @staticmethod
    def get_answers_by_question(form_question_id):
        """Get all answers for a form question"""
        return FormAnswerService.get_answers_by_question(form_question_id)

    @staticmethod
    def update_form_answer(form_answer_id: int, current_user: User, **kwargs) -> tuple:
        """Update a form answer with proper validation"""
        try:
            # Get form answer and validate existence
            form_answer = FormAnswerService.get_form_answer(form_answer_id)
            if not form_answer:
                return None, "Form answer not found"

            # Check authorization
            if not current_user.role.is_super_user:
                if form_answer.form_question.form.creator.environment_id != current_user.environment_id:
                    return None, "Unauthorized access"

            # Check if answer is submitted
            if FormAnswerService.is_answer_submitted(form_answer_id):
                return None, "Cannot update answer that has been submitted"

            # Update the form answer
            return FormAnswerService.update_form_answer(
                form_answer_id=form_answer_id,
                current_user=current_user,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in update_form_answer controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_form_answer(form_answer_id: int) -> Tuple[bool, Union[Dict, str]]:
        """Delete a form answer"""
        try:
            success, result = FormAnswerService.delete_form_answer(form_answer_id)
            return success, result
        except Exception as e:
            logger.error(f"Error in delete_form_answer controller: {str(e)}")
            return False, str(e)

    @staticmethod
    def is_answer_submitted(form_answer_id):
        """Check if answer is submitted"""
        return FormAnswerService.is_answer_submitted(form_answer_id)