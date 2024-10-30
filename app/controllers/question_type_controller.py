from app.services.question_type_service import QuestionTypeService

class QuestionTypeController:
    @staticmethod
    def create_question_type(type_name):
        """
        Create a new question type
        """
        return QuestionTypeService.create_question_type(type_name)

    @staticmethod
    def get_question_type(type_id):
        """
        Get a question type by ID
        """
        return QuestionTypeService.get_question_type(type_id)

    @staticmethod
    def get_all_question_types():
        """
        Get all question types
        """
        return QuestionTypeService.get_all_question_types()

    @staticmethod
    def get_question_type_by_name(type_name):
        """
        Get a question type by name
        """
        return QuestionTypeService.get_question_type_by_name(type_name)

    @staticmethod
    def update_question_type(type_id, new_type_name):
        """
        Update a question type's name
        """
        return QuestionTypeService.update_question_type(type_id, new_type_name)

    @staticmethod
    def delete_question_type(type_id):
        """
        Delete a question type
        """
        return QuestionTypeService.delete_question_type(type_id)