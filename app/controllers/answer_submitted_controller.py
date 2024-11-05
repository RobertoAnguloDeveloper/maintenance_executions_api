# app/controllers/answer_submitted_controller.py

from app.services.answer_submitted_service import AnswerSubmittedService

class AnswerSubmittedController:
    @staticmethod
    def create_answer_submitted(form_answer_id, form_submission_id):
        """Create a new submitted answer"""
        return AnswerSubmittedService.create_answer_submitted(
            form_answer_id=form_answer_id,
            form_submission_id=form_submission_id
        )

    @staticmethod
    def get_answer_submitted(answer_submitted_id):
        """Get a specific submitted answer"""
        return AnswerSubmittedService.get_answer_submitted(answer_submitted_id)

    @staticmethod
    def get_answers_by_submission(submission_id):
        """Get all submitted answers for a form submission"""
        return AnswerSubmittedService.get_answers_by_submission(submission_id)

    @staticmethod
    def delete_answer_submitted(answer_submitted_id):
        """Delete a submitted answer"""
        return AnswerSubmittedService.delete_answer_submitted(answer_submitted_id)