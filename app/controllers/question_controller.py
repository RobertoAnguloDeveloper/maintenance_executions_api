from app.services.question_service import QuestionService

class QuestionController:
    @staticmethod
    def create_question(text, question_type_id, remarks=None):
        """
        Create a new question
        """
        return QuestionService.create_question(text, question_type_id, remarks)
    
    @staticmethod
    def bulk_create_questions(questions_data):
        """Create multiple questions at once"""
        return QuestionService.bulk_create_questions(questions_data)

    @staticmethod
    def get_question(question_id):
        """
        Get a question by ID
        """
        return QuestionService.get_question(question_id)
    
    @staticmethod
    def search_questions(search_query=None, remarks=None, environment_id=None, include_deleted=False):
        questions, error = QuestionService.search_questions(
            search_query=search_query,
            remarks=remarks,
            environment_id=environment_id,
            include_deleted=include_deleted
        )
        if error:
            return []
        return questions
    @staticmethod
    def search_questions_by_type(question_type_id, search_query=None, remarks=None, environment_id=None):
        """
        Search questions of a specific type with filters
        
        Args:
            question_type_id (int): ID of the question type
            search_query (str, optional): Text to search in question text
            remarks (str, optional): Text about the question
            environment_id (int, optional): Filter by environment
            
        Returns:
            list: List of Question objects matching the criteria
        """
        return QuestionService.search_questions_by_type(
            question_type_id=question_type_id,
            search_query=search_query,
            remarks=remarks,
            environment_id=environment_id
        )

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
    def update_question(user, question_id, **kwargs):
        """
        Update a question's details
        """
        return QuestionService.update_question(user, question_id, **kwargs)

    @staticmethod
    def delete_question(question_id):
        """
        Delete a question
        """
        return QuestionService.delete_question(question_id)