# app/controllers/form_question_controller.py

from app.services.form_question_service import FormQuestionService

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
    def get_form_question(form_question_id):
        """Get a specific form question mapping"""
        return FormQuestionService.get_form_question(form_question_id)

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