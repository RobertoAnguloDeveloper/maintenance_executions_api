from app.services.answer_service import AnswerService

class AnswerController:
    @staticmethod
    def create_answer(value, remarks=None):
        """
        Create a new answer
        """
        return AnswerService.create_answer(value, remarks)

    @staticmethod
    def get_answer(answer_id):
        """
        Get an answer by ID
        """
        return AnswerService.get_answer(answer_id)

    @staticmethod
    def get_answers_by_form(form_id):
        """
        Get all answers associated with a form
        """
        return AnswerService.get_answers_by_form(form_id)

    @staticmethod
    def get_all_answers():
        """
        Get all answers
        """
        return AnswerService.get_all_answers()

    @staticmethod
    def update_answer(answer_id, value=None, remarks=None):
        """
        Update an answer
        """
        return AnswerService.update_answer(answer_id, value, remarks)

    @staticmethod
    def delete_answer(answer_id):
        """
        Delete an answer
        """
        return AnswerService.delete_answer(answer_id)

    @staticmethod
    def bulk_create_answers(answers_data):
        """
        Create multiple answers at once
        """
        return AnswerService.bulk_create_answers(answers_data)