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
    def create_question(text, question_type_id, remarks):
        try:
            new_question = Question(
                text=text,
                question_type_id=question_type_id,
                remarks=remarks
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
                    remarks=data.get('remarks')
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
        """Get non-deleted question"""
        return Question.query.filter_by(
            id=question_id, 
            is_deleted=False
        ).first()

    @staticmethod
    def get_questions_by_type(question_type_id):
        """Get non-deleted questions by type"""
        return Question.query.filter_by(
            question_type_id=question_type_id,
            is_deleted=False
        ).order_by(Question.id).all()
    
    @staticmethod
    def search_questions(search_query=None, remarks=None, environment_id=None):
        """Search non-deleted questions"""
        query = Question.query.filter_by(is_deleted=False)

        if search_query:
            query = query.filter(Question.text.ilike(f"%{search_query}%"))

        return query.order_by(Question.text).all()

    @staticmethod
    def search_questions_by_type(question_type_id, search_query=None, remarks=None, environment_id=None):
        """
        Search questions of a specific type with optional filters
        
        Args:
            question_type_id (int): ID of the question type
            search_query (str, optional): Text to search in question text
            remarks (str, optional): Text about the question
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
            if remarks is not None:
                query = query.filter(Question.remarks == remarks)

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
            return query.order_by(Question.id).all()

        except Exception as e:
            logger.error(f"Error searching questions by type: {str(e)}")
            return []

    @staticmethod
    def get_all_questions(include_deleted=False):
        """Get all questions"""
        query = Question.query
        if not include_deleted:
            query = query.filter(Question.is_deleted == False)
        return query.order_by(Question.id).all()

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
        """Soft delete a question"""
        try:
            question = Question.query.get(question_id)
            if not question:
                return False, "Question not found"

            question.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)