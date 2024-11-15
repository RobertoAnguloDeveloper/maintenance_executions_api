# app/controllers/form_answer_controller.py

from app.services.form_answer_service import FormAnswerService

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
    def update_form_answer(form_answer_id, **kwargs):
        """Update a form answer"""
        return FormAnswerService.update_form_answer(form_answer_id, **kwargs)

    @staticmethod
    def delete_form_answer(form_answer_id):
        """Delete a form answer"""
        return FormAnswerService.delete_form_answer(form_answer_id)

    @staticmethod
    def is_answer_submitted(form_answer_id):
        """Check if answer is submitted"""
        return FormAnswerService.is_answer_submitted(form_answer_id)