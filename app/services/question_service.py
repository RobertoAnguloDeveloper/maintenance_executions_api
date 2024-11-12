from tkinter.tix import Form
from app import db
from app.models.form_question import FormQuestion
from app.models.question import Question
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.models.user import User

class QuestionService:
    @staticmethod
    def create_question(text, question_type_id, order_number, has_remarks=False):
        try:
            new_question = Question(
                text=text,
                question_type_id=question_type_id,
                order_number=order_number,
                has_remarks=has_remarks
            )
            db.session.add(new_question)
            db.session.commit()
            return new_question, None
        except IntegrityError:
            db.session.rollback()
            return None, "Error creating question. Please check the question_type_id."
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    @staticmethod
    def bulk_create_questions(questions_data):
        """
        Bulk create questions
        
        Args:
            questions_data (list): List of dictionaries containing question data
            
        Returns:
            tuple: (List of created Question objects, error message)
        """
        try:
            new_questions = []
            
            # Validate all questions first
            for data in questions_data:
                if not data.get('text') or not data.get('question_type_id'):
                    return None, "Text and question_type_id are required for all questions"
                    
                if len(str(data['text']).strip()) < 3:
                    return None, "Question text must be at least 3 characters long"

            # Create all questions
            for data in questions_data:
                question = Question(
                    text=data['text'],
                    question_type_id=data['question_type_id'],
                    order_number=data.get('order_number'),
                    has_remarks=data.get('has_remarks', False)
                )
                db.session.add(question)
                new_questions.append(question)
            
            db.session.commit()
            return new_questions, None
            
        except IntegrityError:
            db.session.rollback()
            return None, "Error creating questions. Please check the question_type_ids."
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_question(question_id):
        return Question.query.get(question_id)

    @staticmethod
    def get_questions_by_type(question_type_id):
        return Question.query.filter_by(question_type_id=question_type_id).order_by(Question.order_number).all()
    
    @staticmethod
    def search_questions(search_query=None, has_remarks=None, environment_id=None):
        """
        Search questions with optional filters
        
        Args:
            search_query (str, optional): Text to search in question text
            has_remarks (bool, optional): Filter by has_remarks flag
            environment_id (int, optional): Filter by environment
            
        Returns:
            list: List of Question objects matching the criteria
        """
        try:
            query = Question.query

            # Text search
            if search_query:
                search_term = f"%{search_query}%"
                query = query.filter(Question.text.ilike(search_term))

            # Has remarks filter
            if has_remarks is not None:
                query = query.filter(Question.has_remarks == has_remarks)

            # Environment filter (if provided)
            if environment_id:
                query = query.join(
                    FormQuestion, 
                    Question.id == FormQuestion.question_id
                ).join(
                    Form, 
                    FormQuestion.form_id == Form.id
                ).join(
                    User, 
                    Form.user_id == User.id
                ).filter(
                    User.environment_id == environment_id
                ).distinct()

            # Order by question text for consistent results
            return query.order_by(Question.text).all()

        except Exception as e:
            logger.error(f"Error searching questions: {str(e)}")
            return []

    @staticmethod
    def search_questions_by_type(question_type_id, search_query=None, has_remarks=None, environment_id=None):
        """
        Search questions of a specific type with optional filters
        
        Args:
            question_type_id (int): ID of the question type
            search_query (str, optional): Text to search in question text
            has_remarks (bool, optional): Filter by has_remarks flag
            environment_id (int, optional): Filter by environment
            
        Returns:
            list: List of Question objects matching the criteria
        """
        try:
            query = Question.query.filter_by(question_type_id=question_type_id)

            # Text search
            if search_query:
                search_term = f"%{search_query}%"
                query = query.filter(Question.text.ilike(search_term))

            # Has remarks filter
            if has_remarks is not None:
                query = query.filter(Question.has_remarks == has_remarks)

            # Environment filter (if provided)
            if environment_id:
                query = query.join(
                    FormQuestion, 
                    Question.id == FormQuestion.question_id
                ).join(
                    Form, 
                    FormQuestion.form_id == Form.id
                ).join(
                    User, 
                    Form.user_id == User.id
                ).filter(
                    User.environment_id == environment_id
                ).distinct()

            # Order by order_number and then text
            return query.order_by(Question.order_number, Question.text).all()

        except Exception as e:
            logger.error(f"Error searching questions by type: {str(e)}")
            return []

    @staticmethod
    def get_all_questions():
        return Question.query.order_by(Question.order_number).all()

    @staticmethod
    def update_question(question_id, **kwargs):
        question = Question.query.get(question_id)
        if question:
            try:
                for key, value in kwargs.items():
                    if hasattr(question, key):
                        setattr(question, key, value)
                db.session.commit()
                return question, None
            except IntegrityError:
                db.session.rollback()
                return None, "Error updating question. Please check the question_type_id."
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Question not found"

    @staticmethod
    def delete_question(question_id):
        question = Question.query.get(question_id)
        if question:
            try:
                db.session.delete(question)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Question not found"