from typing import Dict, Optional, List, Tuple
from app import db
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from datetime import datetime
from typing import List, Optional, Tuple
from datetime import datetime
from app import db
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
import logging

from app.models.form_submission import FormSubmission

logger = logging.getLogger(__name__)

class AnswerSubmittedService:
    @staticmethod
    def validate_text_answer(form_answer: FormAnswer, text_answered: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate text answer based on question type"""
        question_type = form_answer.get_question_type()
        if question_type in ['text', 'date', 'datetime']:
            if not text_answered:
                return False, f"Text answer is required for {question_type} question type"
            if question_type == 'date':
                try:
                    datetime.strptime(text_answered, '%Y-%m-%d')
                except ValueError:
                    return False, "Invalid date format. Use YYYY-MM-DD"
            elif question_type == 'datetime':
                try:
                    datetime.strptime(text_answered, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return False, "Invalid datetime format. Use YYYY-MM-DD HH:MM:SS"
        elif text_answered:
            return False, f"Text answer not allowed for {question_type} question type"
        return True, None

    @staticmethod
    def create_answer_submitted(
        form_answer_id: int,
        form_submission_id: int,
        text_answered: Optional[str] = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        try:
            # Validate form_answer exists
            form_answer = FormAnswer.query.get(form_answer_id)
            if not form_answer:
                return None, "Form answer not found"

            # Validate text answer
            is_valid, error = AnswerSubmittedService.validate_text_answer(
                form_answer, text_answered
            )
            if error:  # Changed condition
                return None, error

            # Check for existing submission
            existing = AnswerSubmitted.query.filter_by(
                form_answer_id=form_answer_id,
                form_submission_id=form_submission_id,
                is_deleted=False
            ).first()
            if existing:
                return None, "Answer already submitted for this submission"

            answer_submitted = AnswerSubmitted(
                form_answer_id=form_answer_id,
                form_submission_id=form_submission_id,
                text_answered=text_answered
            )
            db.session.add(answer_submitted)
            db.session.commit()

            return answer_submitted, None

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in create_answer_submitted: {str(e)}")
            return None, "Database error occurred"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in create_answer_submitted: {str(e)}")
            return None, "Unexpected error occurred"
        
    @staticmethod
    def get_answer_submitted(answer_submitted_id: int) -> Optional[AnswerSubmitted]:
        """Get a specific submitted answer"""
        try:
            return (AnswerSubmitted.query
                .filter_by(
                    id=answer_submitted_id,
                    is_deleted=False
                )
                .join(FormAnswer)
                .join(FormSubmission)
                .options(
                    joinedload(AnswerSubmitted.form_answer),
                    joinedload(AnswerSubmitted.form_submission)
                )
                .first())
        except Exception as e:
            logger.error(f"Error getting answer submitted {answer_submitted_id}: {str(e)}")
            return None

    @staticmethod
    def get_all_answers_submitted(filters: Dict = None) -> List[AnswerSubmitted]:
        query = AnswerSubmitted.query.filter_by(is_deleted=False)
        if filters:
            if 'form_submission_id' in filters:
                query = query.filter_by(form_submission_id=filters['form_submission_id'])
        return query.all()

    @staticmethod
    def get_answers_by_submission(submission_id: int) -> Tuple[List[AnswerSubmitted], Optional[str]]:
        """Get all submitted answers for a form submission"""
        try:
            answers = (AnswerSubmitted.query
                .filter_by(
                    form_submission_id=submission_id,
                    is_deleted=False
                )
                .options(
                    joinedload(AnswerSubmitted.form_answer),
                    joinedload(AnswerSubmitted.form_submission)
                )
                .all())
            return answers, None
        except Exception as e:
            logger.error(f"Error getting answers by submission: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_answer_submitted(answer_submitted_id: int, text_answered: Optional[str] = None) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        try:
            answer = AnswerSubmitted.query.get(answer_submitted_id)
            if not answer:
                return None, "Answer submission not found"
            
            answer.text_answered = text_answered
            db.session.commit()
            return answer, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_answer_submitted(answer_submitted_id: int) -> Tuple[bool, Optional[str]]:
        try:
            answer = AnswerSubmitted.query.get(answer_submitted_id)
            if not answer:
                return False, "Answer submission not found"
            
            answer.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)