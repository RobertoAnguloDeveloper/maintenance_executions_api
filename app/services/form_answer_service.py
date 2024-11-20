# app/services/form_answer_service.py

from typing import Optional, Union
from app import db
from app.models.answer import Answer
from app.models.answers_submitted import AnswerSubmitted
from app.models.form import Form
from app.models.form_answer import FormAnswer
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.orm import joinedload
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
    def bulk_create_form_answers(
        form_answers_data: list[dict]
    ) -> tuple[Optional[list[FormAnswer]], Optional[str]]:
        """Create multiple form answers with validation"""
        try:
            created_answers = []
            
            # Start transaction
            db.session.begin_nested()

            for data in form_answers_data:
                # Validate form question exists and is not deleted
                form_question = FormQuestion.query.filter_by(
                    id=data['form_question_id'],
                    is_deleted=False
                ).first()
                
                if not form_question:
                    db.session.rollback()
                    return None, f"Form question {data['form_question_id']} not found"

                # Validate answer exists and is not deleted
                answer = Answer.query.filter_by(
                    id=data['answer_id'],
                    is_deleted=False
                ).first()
                
                if not answer:
                    db.session.rollback()
                    return None, f"Answer {data['answer_id']} not found"

                # Check for existing non-deleted mapping
                existing = FormAnswer.query.filter_by(
                    form_question_id=data['form_question_id'],
                    answer_id=data['answer_id'],
                    is_deleted=False
                ).first()
                
                if existing:
                    db.session.rollback()
                    return None, "This answer is already mapped to the question"

                form_answer = FormAnswer(
                    form_question_id=data['form_question_id'],
                    answer_id=data['answer_id']
                )
                db.session.add(form_answer)
                created_answers.append(form_answer)

            # Commit all changes
            db.session.commit()
            return created_answers, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating form answers: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        
    @staticmethod
    def get_all_form_answers(include_deleted=False):
        """Get all form answers"""
        query = FormAnswer.query
        
        if not include_deleted:
            query = query.filter(FormAnswer.is_deleted == False)
            
        return query.order_by(FormAnswer.id).all()

    @staticmethod
    def get_form_answer(form_answer_id: int) -> Optional[FormAnswer]:
        """Get non-deleted form answer by ID with relationships"""
        return (FormAnswer.query
            .filter_by(
                id=form_answer_id,
                is_deleted=False
            )
            .options(
                joinedload(FormAnswer.form_question)
                    .joinedload(FormQuestion.form)
                    .joinedload(Form.creator),
                joinedload(FormAnswer.answer)
            )
            .first())

    @staticmethod
    def get_answers_by_question(form_question_id: int) -> list[FormAnswer]:
        """Get all non-deleted answers for a form question"""
        return (FormAnswer.query
            .filter_by(
                form_question_id=form_question_id,
                is_deleted=False
            )
            .options(
                joinedload(FormAnswer.answer)
            )
            .order_by(FormAnswer.id)
            .all())

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
    def delete_form_answer(form_answer_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a form answer and associated data through cascade soft delete
        
        Args:
            form_answer_id (int): ID of the form answer to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            form_answer = FormAnswer.query.filter_by(
                id=form_answer_id,
                is_deleted=False
            ).first()
            
            if not form_answer:
                return False, "Form answer not found"

            # Check if answer is submitted
            submitted = AnswerSubmitted.query.filter_by(
                form_answers_id=form_answer_id,
                is_deleted=False
            ).first()
            
            if submitted:
                return False, "Cannot delete answer that has been submitted"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'answers_submitted': 0
            }

            # Soft delete any submitted answers (even if marked as deleted)
            submitted_answers = AnswerSubmitted.query.filter_by(
                form_answers_id=form_answer_id
            ).all()

            for submitted in submitted_answers:
                if not submitted.is_deleted:
                    submitted.soft_delete()
                    deletion_stats['answers_submitted'] += 1

            # Finally soft delete the form answer
            form_answer.soft_delete()

            # Commit all changes
            db.session.commit()
            
            logger.info(f"Form answer {form_answer_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting form answer: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def is_answer_submitted(form_answer_id: int) -> bool:
        """Check if answer is submitted"""
        return (AnswerSubmitted.query
            .filter_by(
                form_answers_id=form_answer_id,
                is_deleted=False
            )
            .first() is not None)