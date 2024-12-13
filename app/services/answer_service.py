from typing import Optional, Union
from app import db
from app.models.answer import Answer
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
import logging

from app.models.form_question import FormQuestion

logger = logging.getLogger(__name__)

class AnswerService:
    @staticmethod
    def create_answer(value, remarks=None):
        """
        Create a new answer with the given value and optional remarks
        """
        try:
            new_answer = Answer(
                value=value,
                remarks=remarks
            )
            db.session.add(new_answer)
            db.session.commit()
            return new_answer, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_answer(answer_id: int) -> Optional[Answer]:
        """Get non-deleted answer by ID"""
        return Answer.query.filter_by(
            id=answer_id,
            is_deleted=False
        ).first()

    @staticmethod
    def get_answers_by_form(form_id: int) -> list[Answer]:
        """Get all non-deleted answers for a specific form"""
        return (Answer.query
            .join(FormAnswer)
            .join(FormQuestion)
            .filter(
                FormQuestion.form_id == form_id,
                Answer.is_deleted == False,
                FormAnswer.is_deleted == False,
                FormQuestion.is_deleted == False
            )
            .distinct()
            .all())

    @staticmethod
    def get_all_answers(include_deleted: bool = False) -> list[Answer]:
        """Get all answers with optional inclusion of deleted records"""
        query = Answer.query
        
        if not include_deleted:
            query = query.filter(Answer.is_deleted == False)
            
        return query.order_by(Answer.id).all()

    @staticmethod
    def update_answer(
        answer_id: int,
        value: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> tuple[Optional[Answer], Optional[str]]:
        """Update an answer with validation"""
        try:
            answer = Answer.query.filter_by(
                id=answer_id,
                is_deleted=False
            ).first()
            
            if not answer:
                return None, "Answer not found"


            if remarks is not None:
                answer.remarks = remarks

            answer.updated_at = datetime.utcnow()
            db.session.commit()

            return answer, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error updating answer: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def delete_answer(answer_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete an answer with cascade soft delete
        
        Args:
            answer_id (int): ID of the answer to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            answer = Answer.query.filter_by(
                id=answer_id,
                is_deleted=False
            ).first()
            
            if not answer:
                return False, "Answer not found"

            # Check if answer is in use
            active_form_answers = FormAnswer.query.filter_by(
                answer_id=answer_id,
                is_deleted=False
            ).count()
            
            if active_form_answers > 0:
                return False, f"Answer is in use in {active_form_answers} form answers"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'form_answers': 0,
                'answers_submitted': 0
            }

            # 1. Find all form answers using this answer (including deleted forms)
            form_answers = FormAnswer.query.filter_by(
                answer_id=answer_id
            ).all()

            for fa in form_answers:
                if not fa.is_deleted:
                    fa.soft_delete()
                    deletion_stats['form_answers'] += 1

                    # 2. Find and delete submitted answers
                    submitted_answers = AnswerSubmitted.query.filter_by(
                        form_answers_id=fa.id,
                        is_deleted=False
                    ).all()

                    for submitted in submitted_answers:
                        submitted.soft_delete()
                        deletion_stats['answers_submitted'] += 1

            # Finally soft delete the answer
            answer.soft_delete()

            # Commit all changes
            db.session.commit()
            
            logger.info(f"Answer {answer_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting answer: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def bulk_create_answers(answers_data: list[dict]) -> tuple[Optional[list[Answer]], Optional[str]]:
        """Create multiple answers at once with validation"""
        try:
            created_answers = []
            for data in answers_data:

                answer = Answer(
                    value=data['value'],
                    remarks=data.get('remarks')
                )
                db.session.add(answer)
                created_answers.append(answer)

            db.session.commit()
            return created_answers, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating answers: {str(e)}"
            logger.error(error_msg)
            return None, error_msg