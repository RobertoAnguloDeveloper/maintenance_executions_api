from tkinter.tix import Form
from typing import Optional, Union
from app import db
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
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
        search_query: Optional[str] = None,
        remarks: Optional[str] = None,
        environment_id: Optional[int] = None,
        include_deleted: bool = False
    ) -> list[Question]:
        """Search questions with filters"""
        query = Question.query

        if not include_deleted:
            query = query.filter(Question.is_deleted == False)

        if search_query:
            query = query.filter(Question.text.ilike(f"%{search_query}%"))

        if remarks:
            query = query.filter(Question.remarks.ilike(f"%{remarks}%"))

        if environment_id:
            query = query.join(
                FormQuestion,
                Form,
                User
            ).filter(
                User.environment_id == environment_id,
                User.is_deleted == False
            )

        return query.order_by(Question.text).distinct().all()

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
                Form,
                User
            ).filter(
                User.environment_id == environment_id,
                User.is_deleted == False
            )

        return query.order_by(Question.text).distinct().all()

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
    def delete_question(question_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a question and associated data through cascade soft delete
        
        Args:
            question_id (int): ID of the question to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            question = Question.query.filter_by(
                id=question_id,
                is_deleted=False
            ).first()
            
            if not question:
                return False, "Question not found"

            # Check if question is in use in active forms
            active_forms = (FormQuestion.query
                .join(Form)
                .filter(
                    FormQuestion.question_id == question_id,
                    FormQuestion.is_deleted == False,
                    Form.is_deleted == False
                ).count())
                
            if active_forms > 0:
                return False, f"Question is in use in {active_forms} active forms"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'form_questions': 0,
                'form_answers': 0,
                'answers_submitted': 0
            }

            # 1. Get all form questions (including deleted forms)
            form_questions = FormQuestion.query.filter_by(
                question_id=question_id,
                is_deleted=False
            ).all()

            for fq in form_questions:
                # Soft delete form question
                fq.soft_delete()
                deletion_stats['form_questions'] += 1

                # 2. Soft delete form answers
                form_answers = FormAnswer.query.filter_by(
                    form_question_id=fq.id,
                    is_deleted=False
                ).all()

                for fa in form_answers:
                    fa.soft_delete()
                    deletion_stats['form_answers'] += 1

                    # 3. Soft delete submitted answers
                    answers_submitted = AnswerSubmitted.query.filter_by(
                        form_answers_id=fa.id,
                        is_deleted=False
                    ).all()

                    for ans in answers_submitted:
                        ans.soft_delete()
                        deletion_stats['answers_submitted'] += 1

            # Finally soft delete the question
            question.soft_delete()

            # Commit all changes
            db.session.commit()
            
            logger.info(f"Question {question_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting question: {str(e)}"
            logger.error(error_msg)
            return False, error_msg