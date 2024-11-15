# app/services/form_answer_service.py

from app import db
from app.models.answer import Answer
from app.models.form_answer import FormAnswer
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.models.form_question import FormQuestion

class FormAnswerService:
    @staticmethod
    def create_form_answer(form_question_id: int, answer_id: int) -> tuple:
        """
        Create a new form answer
        
        Args:
            form_question_id (int): Form question ID
            answer_id (int): Answer ID
            
        Returns:
            tuple: (FormAnswer, str) - Created form answer or error message
        """
        try:
            # Validate form question exists
            form_question = FormQuestion.query.get(form_question_id)
            if not form_question:
                return None, "Form question not found"

            # Validate answer exists
            answer = Answer.query.get(answer_id)
            if not answer:
                return None, "Answer not found"

            # Create form answer
            form_answer = FormAnswer(
                form_question_id=form_question_id,
                answer_id=answer_id
            )
            
            db.session.add(form_answer)
            db.session.commit()
            
            # Refresh to load relationships
            db.session.refresh(form_answer)
            
            return form_answer, None

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating form answer: {str(e)}")
            return None, "Invalid form_question_id or answer_id"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form answer: {str(e)}")
            return None, str(e)

    @staticmethod
    def bulk_create_form_answers(form_answers_data):
        """Bulk create form answers"""
        try:
            form_answers = []
            for data in form_answers_data:
                form_answer = FormAnswer(
                    form_question_id=data['form_question_id'],
                    answer_id=data['answer_id']
                )
                form_answers.append(form_answer)

            db.session.bulk_save_objects(form_answers)
            db.session.commit()
            return form_answers, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_question_id or answer_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    @staticmethod
    def get_all_form_answers(include_deleted=False):
        """Get all form answers"""
        query = FormAnswer.query
        
        if not include_deleted:
            query = query.filter(FormAnswer.is_deleted == False)
            
        return query.order_by(FormAnswer.id).all()

    @staticmethod
    def get_form_answer(form_answer_id):
        """Get a specific form answer"""
        return FormAnswer.query.get(form_answer_id)

    @staticmethod
    def get_answers_by_question(form_question_id):
        """Get all answers for a form question"""
        return FormAnswer.query.filter_by(form_question_id=form_question_id).all()

    @staticmethod
    def update_form_answer(form_answer_id, **kwargs):
        """Update a form answer"""
        try:
            form_answer = FormAnswer.query.get(form_answer_id)
            if not form_answer:
                return None, "Form answer not found"

            for key, value in kwargs.items():
                if hasattr(form_answer, key):
                    setattr(form_answer, key, value)

            form_answer.updated_at = datetime.utcnow()
            db.session.commit()
            return form_answer, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid answer_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_form_answer(form_answer_id):
        """Soft delete a form answer"""
        try:
            form_answer = FormAnswer.query.get(form_answer_id)
            if not form_answer:
                return False, "Form answer not found"

            form_answer.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def is_answer_submitted(form_answer_id):
        """Check if answer is submitted"""
        form_answer = FormAnswer.query.get(form_answer_id)
        return form_answer and len(form_answer.submissions) > 0