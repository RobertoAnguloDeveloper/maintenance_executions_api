from app.services.question_service import QuestionService

class QuestionController:
    @staticmethod
    def create_question(text, question_type_id, has_remarks=False):
        """
        Create a new question
        """
        return QuestionService.create_question(text, question_type_id, has_remarks)
    
    @staticmethod
    def bulk_create_questions(questions_data):
        """
        Create multiple questions at once
        
        Args:
            questions_data (list): List of dictionaries containing question data
            
        Returns:
            tuple: (List of created Question objects, error message)
        """
        return QuestionService.bulk_create_questions(questions_data)

    @staticmethod
    def get_question(question_id):
        """
        Get a question by ID
        """
        return QuestionService.get_question(question_id)
    
    @staticmethod
    def search_questions(search_query=None, has_remarks=None, environment_id=None):
        """
        Search questions with filters
        
        Args:
            search_query (str, optional): Text to search in question text
            has_remarks (bool, optional): Filter by has_remarks flag
            environment_id (int, optional): Filter by environment
            
        Returns:
            list: List of Question objects matching the criteria
        """
        return QuestionService.search_questions(
            search_query=search_query,
            has_remarks=has_remarks,
            environment_id=environment_id
        )

    @staticmethod
    def search_questions_by_type(question_type_id, search_query=None, has_remarks=None, environment_id=None):
        """
        Search questions of a specific type with filters
        
        Args:
            question_type_id (int): ID of the question type
            search_query (str, optional): Text to search in question text
            has_remarks (bool, optional): Filter by has_remarks flag
            environment_id (int, optional): Filter by environment
            
        Returns:
            list: List of Question objects matching the criteria
        """
        return QuestionService.search_questions_by_type(
            question_type_id=question_type_id,
            search_query=search_query,
            has_remarks=has_remarks,
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