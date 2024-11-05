# app/controllers/form_answer_controller.py

from app.services.form_answer_service import FormAnswerService

class FormAnswerController:
    @staticmethod
    def create_form_answer(form_question_id, answer_id, remarks=None):
        """Create a new form answer"""
        return FormAnswerService.create_form_answer(
            form_question_id=form_question_id,
            answer_id=answer_id,
            remarks=remarks
        )

    @staticmethod
    def bulk_create_form_answers(form_answers_data):
        """Bulk create form answers"""
        return FormAnswerService.bulk_create_form_answers(form_answers_data)

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