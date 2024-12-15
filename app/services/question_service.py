from app.models.form import Form
from typing import Any, Dict, List, Optional, Tuple, Union
from app import db
from app.models.answer_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.question import Question
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.models.question_type import QuestionType
from app.models.user import User

class QuestionService:
    @staticmethod
    def create_question(
        text: str,
        question_type_id: int,
        remarks: Optional[str]
    ) -> Tuple[Optional[Question], Optional[str]]:
        """
        Create a new question with validation.
        
        Args:
            text: Question text
            question_type_id: ID of the question type
            remarks: Optional remarks
            current_user: Current user object for authorization
            
        Returns:
            tuple: (Created Question object or None, Error message or None)
        """
        try:
            # Validate question text
            if not text or len(text.strip()) < 3:
                return None, "Question text must be at least 3 characters long"

            # Verify question type exists and is not deleted
            question_type = QuestionType.query.filter_by(
                id=question_type_id,
                is_deleted=False
            ).first()
            
            if not question_type:
                return None, "Question type not found or has been deleted"

            # Start transaction
            db.session.begin_nested()

            new_question = Question(
                text=text,
                question_type_id=question_type_id,
                remarks=remarks
            )
            db.session.add(new_question)
            db.session.commit()

            logger.info(
                f"Question created successfully"
            )
            return new_question, None

        except IntegrityError as e:
            db.session.rollback()
            error_msg = "Database integrity error"
            logger.error(f"{error_msg}: {str(e)}")
            return None, error_msg
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating question: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        
    @staticmethod
    def bulk_create_questions(questions_data: List[Dict[str, Any]]) -> Tuple[Optional[List[Question]], Optional[str]]:
        try:
            if not questions_data:
                return None, "No questions provided"

            db.session.begin_nested()
            created_questions = []

            for data in questions_data:
                if not data.get('text') or len(str(data['text']).strip()) < 3:
                    db.session.rollback()
                    return None, "Question text must be at least 3 characters long"

                question_type = QuestionType.query.filter_by(
                    id=data.get('question_type_id'),
                    is_deleted=False
                ).first()
                
                if not question_type:
                    db.session.rollback() 
                    return None, f"Question type {data.get('question_type_id')} not found or deleted"

            for data in questions_data:
                question = Question(
                    text=data['text'],
                    question_type_id=data['question_type_id'],
                    remarks=data.get('remarks')
                )
                db.session.add(question)
                created_questions.append(question)

            db.session.commit()
            return created_questions, None

        except Exception as e:
            db.session.rollback()
            return None, f"Error in bulk question creation: {str(e)}"

    @staticmethod
    def get_question(question_id: int) -> Optional[Question]:
        """Get non-deleted question by ID"""
        return Question.query.filter_by(
            id=question_id,
            is_deleted=False
        ).first()

    @staticmethod
    def get_questions_by_type(
        question_type_id: int,
        include_deleted: bool = False
    ) -> list[Question]:
        """Get all questions of a specific type"""
        query = Question.query.filter_by(question_type_id=question_type_id)
        
        if not include_deleted:
            query = query.filter(Question.is_deleted == False)
            
        return query.order_by(Question.id).all()
    
    @staticmethod
    def search_questions(
        search_query = None,
        remarks = None,
        question_type_id = None,
        environment_id= None,
        current_user: User = None,
        include_deleted=False
    ) -> list[Question]:
        """
        Search questions with filters and proper soft-delete handling.
        
        Args:
            search_query: Optional text to search in question text
            question_type_id: Optional question type filter
            environment_id: Optional environment filter
            current_user: Current user object for authorization
            
        Returns:
            tuple: (List of Question objects, Error message or None)
        """
        try:
            query = Question.query.filter_by(is_deleted=False)

            # Apply search filters
            if search_query:
                query = query.filter(
                    or_(
                        Question.text.ilike(f"%{search_query}%"),
                        Question.remarks.ilike(f"%{search_query}%")
                    )
                )

            if question_type_id:
                query = query.filter(Question.question_type_id == question_type_id)

            # Apply environment filter for non-admin users
            if environment_id and current_user and not current_user.role.is_super_user:
                query = query.join(
                    FormQuestion,
                    Form,
                    User
                ).filter(
                    User.environment_id == environment_id,
                    User.is_deleted == False,
                    Form.is_deleted == False,
                    FormQuestion.is_deleted == False
                )

            questions = query.order_by(Question.text).distinct().all()
            return questions, None

        except Exception as e:
            error_msg = f"Error searching questions: {str(e)}"
            logger.error(error_msg)
            return [], error_msg
        
    @staticmethod
    def get_questions_by_environment(environment_id: int) -> list[Question]:
        """
        Get all non-deleted questions associated with an environment
        
        Args:
            environment_id: ID of the environment to filter by

        Returns:
            List of Question objects
        """
        try:
            questions = (Question.query
                .join(FormQuestion, FormQuestion.question_id == Question.id)
                .join(Form, Form.id == FormQuestion.form_id)
                .join(User, User.id == Form.user_id)
                .filter(
                    User.environment_id == environment_id,
                    Question.is_deleted == False,
                    FormQuestion.is_deleted == False,
                    Form.is_deleted == False,
                    User.is_deleted == False
                )
                .distinct()
                .order_by(Question.text)
                .all())
            
            return questions

        except Exception as e:
            logger.error(f"Error getting questions by environment: {str(e)}")
            return []

    @staticmethod
    def search_questions_by_type(
        question_type_id: int,
        search_query: Optional[str] = None,
        remarks: Optional[str] = None,
        environment_id: Optional[int] = None
    ) -> list[Question]:
        """Search questions of a specific type with filters"""
        query = Question.query.filter_by(
            question_type_id=question_type_id,
            is_deleted=False
        )

        if search_query:
            query = query.filter(Question.text.ilike(f"%{search_query}%"))

        if remarks:
            query = query.filter(Question.remarks.ilike(f"%{remarks}%"))

        if environment_id:
            query = query.join(
                FormQuestion,
                FormQuestion.question_id == Question.id
            ).join(
                Form,
                Form.id == FormQuestion.form_id
            ).join(
                User,
                User.id == Form.user_id
            ).filter(
                User.environment_id == environment_id,
                User.is_deleted == False,
                Form.is_deleted == False,
                FormQuestion.is_deleted == False
            )

        return query.distinct().order_by(Question.text).all()

    @staticmethod
    def get_all_questions(include_deleted=False):
        """Get all questions"""
        query = Question.query
        if not include_deleted:
            query = query.filter(Question.is_deleted == False)
        return query.order_by(Question.id).all()

    @staticmethod
    def update_question(
        user: User,
        question_id: int,
        **kwargs
    ) -> Tuple[Optional[Question], Optional[str]]:
        """
        Update a question with validation and soft-delete checking.
        
        Args:
            question_id: ID of the question to update
            current_user: Current user object for authorization
            **kwargs: Fields to update
            
        Returns:
            tuple: (Updated Question object or None, Error message or None)
        """
        try:
            # Verify question exists and is not deleted
            question = Question.query.filter_by(
                id=question_id,
                is_deleted=False
            ).first()
            
            if not question:
                return None, "Question not found or has been deleted"

            # Validate text if provided
            if 'text' in kwargs:
                if not kwargs['text'] or len(kwargs['text'].strip()) < 3:
                    return None, "Question text must be at least 3 characters long"

            # Validate question type if provided
            if 'question_type_id' in kwargs:
                question_type = QuestionType.query.filter_by(
                    id=kwargs['question_type_id'],
                    is_deleted=False
                ).first()
                
                if not question_type:
                    return None, "Question type not found or has been deleted"

            # Check if question is in use
            if FormQuestion.query.filter_by(
                question_id=question_id,
                is_deleted=False
            ).first():
                # Only allow updating remarks if question is in use
                if set(kwargs.keys()) - {'remarks'}:
                    return None, "Cannot modify question that is in use (except remarks)"

            # Start transaction
            db.session.begin_nested()

            # Update fields
            for key, value in kwargs.items():
                if hasattr(question, key):
                    setattr(question, key, value)

            question.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Question {question_id} updated by user {user.username}")
            return question, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error updating question: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def delete_question(
        question_id: int,
        current_user: User
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a question with cascade soft delete.
        
        Args:
            question_id: ID of the question to delete
            current_user: Current user object for authorization
            
        Returns:
            tuple: (Success boolean, Error message or None)
        """
        try:
            # Verify question exists and is not deleted
            question = Question.query.filter_by(
                id=question_id,
                is_deleted=False
            ).first()
            
            if not question:
                return False, "Question not found or has been deleted"

            # Check for active form questions
            active_forms = FormQuestion.query.filter_by(
                question_id=question_id,
                is_deleted=False
            ).count()
            
            if active_forms > 0:
                return False, f"Cannot delete question used in {active_forms} active forms"

            # Start transaction
            db.session.begin_nested()

            # Soft delete related data
            form_questions = FormQuestion.query.filter_by(
                question_id=question_id
            ).all()

            for fq in form_questions:
                if not fq.is_deleted:
                    fq.is_deleted = True
                    fq.deleted_at = datetime.utcnow()

                # Soft delete related form answers
                form_answers = FormAnswer.query.filter_by(
                    form_question_id=fq.id,
                    is_deleted=False
                ).all()

                for fa in form_answers:
                    fa.is_deleted = True
                    fa.deleted_at = datetime.utcnow()

                    # Soft delete submitted answers
                    submitted_answers = AnswerSubmitted.query.filter_by(
                        form_answers_id=fa.id,
                        is_deleted=False
                    ).all()

                    for sa in submitted_answers:
                        sa.is_deleted = True
                        sa.deleted_at = datetime.utcnow()

            # Finally soft delete the question
            question.is_deleted = True
            question.deleted_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Question {question_id} deleted by user {current_user.username}")
            return True, 1

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting question: {str(e)}"
            logger.error(error_msg)
            return False, error_msg