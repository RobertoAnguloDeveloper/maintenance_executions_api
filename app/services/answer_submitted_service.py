from typing import Optional, Union, List, Dict, Any, Tuple
from app import db
from app.models.answers_submitted import AnswerSubmitted
from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.models.question_type import QuestionType
from app.models.user import User
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedService:
    @staticmethod
    def create_answer_submitted(
        form_answers_id: int, 
        form_submissions_id: int, 
        text_answered: str = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        """
        Create a new submitted answer with proper handling of text-based answers
        
        Args:
            form_answers_id: ID of the form answer
            form_submissions_id: ID of the form submission
            text_answered: Optional text answer for text-based questions
            
        Returns:
            tuple: (Created AnswerSubmitted object or None, Error message or None)
        """
        try:
            # Verify form_answer exists and get its question type
            form_answer = FormAnswer.query.options(
                joinedload(FormAnswer.form_question)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type)
            ).get(form_answers_id)

            if not form_answer:
                return None, "Form answer not found"

            # Verify form submission exists
            form_submission = FormSubmission.query.get(form_submissions_id)
            if not form_submission:
                return None, "Form submission not found"

            # Get question type
            question_type = form_answer.form_question.question.question_type.type
            is_text_based = question_type in ['text', 'date', 'datetime']

            # Validate text answer requirements
            if is_text_based:
                if not text_answered:
                    return None, f"Text answer is required for {question_type} questions"
                    
                # Validate date/datetime formats
                if question_type in ['date', 'datetime']:
                    try:
                        if question_type == 'date':
                            datetime.strptime(text_answered, '%Y-%m-%d')
                        else:
                            datetime.strptime(text_answered, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return None, f"Invalid format for {question_type}"
            else:
                # For non-text based questions, ensure text_answered is None
                text_answered = None

            # Check for existing submission
            existing = AnswerSubmitted.query.filter_by(
                form_answers_id=form_answers_id,
                form_submissions_id=form_submissions_id,
                is_deleted=False
            ).first()
            
            if existing:
                return None, "Answer already submitted for this submission"

            # Create new answer submission
            answer_submitted = AnswerSubmitted(
                form_answers_id=form_answers_id,
                form_submissions_id=form_submissions_id,
                text_answered=text_answered
            )
            
            db.session.add(answer_submitted)
            db.session.commit()
            
            return answer_submitted, None

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Database integrity error: {str(e)}")
            return None, "Database integrity error"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating answer submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_answer_submitted(answer_submitted_id: int) -> Optional[AnswerSubmitted]:
        """Get a specific submitted answer"""
        return (AnswerSubmitted.query
            .filter_by(id=answer_submitted_id, is_deleted=False)
            .options(
                joinedload(AnswerSubmitted.form_answer)
                .joinedload(FormAnswer.form_question)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type)
            ).first())

    @staticmethod
    def get_answers_by_submission(submission_id: int) -> List[AnswerSubmitted]:
        """Get all submitted answers for a form submission"""
        return (AnswerSubmitted.query
            .filter_by(form_submissions_id=submission_id, is_deleted=False)
            .options(
                joinedload(AnswerSubmitted.form_answer)
                .joinedload(FormAnswer.form_question)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type)
            ).all())

    @staticmethod
    def update_answer_submitted(
        answer_submitted_id: int,
        text_answered: str = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        """Update a submitted answer"""
        try:
            answer_submitted = AnswerSubmitted.query.get(answer_submitted_id)
            if not answer_submitted:
                return None, "Answer submission not found"

            # Validate text answer if question type requires it
            if answer_submitted.requires_text_answer():
                if text_answered is None:
                    return None, "Text answer is required for this question type"
                    
                # Validate date/datetime formats
                question_type = answer_submitted.form_answer.form_question.question.question_type.type
                if question_type in ['date', 'datetime']:
                    try:
                        if question_type == 'date':
                            datetime.strptime(text_answered, '%Y-%m-%d')
                        else:
                            datetime.strptime(text_answered, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return None, f"Invalid format for {question_type}"

            answer_submitted.text_answered = text_answered
            answer_submitted.updated_at = datetime.utcnow()
            
            db.session.commit()
            return answer_submitted, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating answer submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_answer_submitted(answer_submitted_id: int) -> Tuple[bool, Optional[str]]:
        """Delete a submitted answer"""
        try:
            answer_submitted = AnswerSubmitted.query.get(answer_submitted_id)
            if not answer_submitted:
                return False, "Answer submission not found"

            answer_submitted.soft_delete()
            db.session.commit()
            
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting answer submission: {str(e)}")
            return False, str(e)