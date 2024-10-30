from app.services.question_service import QuestionService

class QuestionController:
    @staticmethod
    def create_question(text, question_type_id, order_number, has_remarks=False):
        """
        Create a new question
        """
        return QuestionService.create_question(text, question_type_id, order_number, has_remarks)

    @staticmethod
    def get_question(question_id):
        """
        Get a question by ID
        """
        return QuestionService.get_question(question_id)

    @staticmethod
    def get_questions_by_type(question_type_id):
        """
        Get all questions of a specific type
        """
        return QuestionService.get_questions_by_type(question_type_id)

    @staticmethod
    def get_all_questions():
        """
        Get all questions
        """
        return QuestionService.get_all_questions()

    @staticmethod
    def update_question(question_id, **kwargs):
        """
        Update a question's details
        """
        return QuestionService.update_question(question_id, **kwargs)

    @staticmethod
    def delete_question(question_id):
        """
        Delete a question
        """
        return QuestionService.delete_question(question_id)

    @staticmethod
    def reorder_questions(questions_order):
        """
        Reorder multiple questions
        """
        return QuestionService.reorder_questions(questions_order)