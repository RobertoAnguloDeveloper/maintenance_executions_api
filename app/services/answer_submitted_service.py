# app/services/answer_submitted_service.py

from typing import Optional, Union
from app import db
from app.models.answers_submitted import AnswerSubmitted
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from datetime import datetime

from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedService:
    @staticmethod
    def create_answer_submitted(form_answers_id, form_submissions_id):
        """Create a new submitted answer"""
        try:
            # Check if answer already submitted for this submission
            existing = AnswerSubmitted.query.filter_by(
                form_answers_id=form_answers_id,
                form_submissions_id=form_submissions_id
            ).first()
            
            if existing:
                return None, "Answer already submitted for this submission"

            answer_submitted = AnswerSubmitted(
                form_answers_id=form_answers_id,
                form_submissions_id=form_submissions_id
            )
            db.session.add(answer_submitted)
            db.session.commit()
            return answer_submitted, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_answers_id or form_submissions_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)
        
    @staticmethod
    def get_all_answers_submitted(filters: dict = None) -> list:
        """
        Get all answers submitted with optional filters
        
        Args:
            filters (dict): Optional filters including:
                - form_id (int): Filter by specific form
                - environment_id (int): Filter by environment
                - submitted_by (str): Filter by submitter
                - start_date (datetime): Filter by start date
                - end_date (datetime): Filter by end date
                
        Returns:
            list: List of AnswerSubmitted objects
        """
        try:
            query = AnswerSubmitted.query.filter_by(is_deleted=False)

            if filters:
                if filters.get('form_id'):
                    query = query.join(FormSubmission).filter(
                        FormSubmission.form_id == filters['form_id']
                    )
                    
                if filters.get('environment_id'):
                    query = query.join(FormSubmission)\
                        .join(Form)\
                        .join(User)\
                        .filter(User.environment_id == filters['environment_id'])
                    
                if filters.get('submitted_by'):
                    query = query.join(FormSubmission)\
                        .filter(FormSubmission.submitted_by == filters['submitted_by'])
                    
                if filters.get('start_date'):
                    query = query.join(FormSubmission)\
                        .filter(FormSubmission.submitted_at >= filters['start_date'])
                    
                if filters.get('end_date'):
                    query = query.join(FormSubmission)\
                        .filter(FormSubmission.submitted_at <= filters['end_date'])

            # Order by most recent first
            query = query.order_by(AnswerSubmitted.created_at.desc())
            
            return query.all()

        except Exception as e:
            logger.error(f"Error getting all answers submitted: {str(e)}")
            return []

    @staticmethod
    def get_answer_submitted(answer_submitted_id: int) -> Optional[AnswerSubmitted]:
        """Get non-deleted submitted answer with relationships"""
        return (AnswerSubmitted.query
            .filter_by(
                id=answer_submitted_id,
                is_deleted=False
            )
            .options(
                joinedload(AnswerSubmitted.form_submission)
                    .joinedload(FormSubmission.form)
                    .joinedload(Form.creator),
                joinedload(AnswerSubmitted.form_answer)
                    .joinedload(FormAnswer.answer)
            )
            .first())

    @staticmethod
    def get_answers_by_submission(
        submission_id: int,
        include_deleted: bool = False
    ) -> list[AnswerSubmitted]:
        """Get submitted answers for a submission"""
        query = AnswerSubmitted.query.filter_by(
            form_submissions_id=submission_id
        )
        
        if not include_deleted:
            query = query.filter(AnswerSubmitted.is_deleted == False)
            
        return (query
            .options(
                joinedload(AnswerSubmitted.form_answer)
                    .joinedload(FormAnswer.answer)
            )
            .order_by(AnswerSubmitted.created_at)
            .all())

    @staticmethod
    def delete_answer_submitted(answer_submitted_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a submitted answer
        
        Args:
            answer_submitted_id (int): ID of the submitted answer to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            answer_submitted = AnswerSubmitted.query.filter_by(
                id=answer_submitted_id,
                is_deleted=False
            ).first()
            
            if not answer_submitted:
                return False, "Submitted answer not found"

            # Start transaction
            db.session.begin_nested()

            # Soft delete the submitted answer
            answer_submitted.soft_delete()

            # Commit changes
            db.session.commit()
            
            logger.info(f"Submitted answer {answer_submitted_id} soft deleted")
            return True, {"answers_submitted": 1}

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting submitted answer: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def get_answers_by_user(username: str) -> list[AnswerSubmitted]:
        """Get all non-deleted submitted answers for a specific user"""
        return (AnswerSubmitted.query
            .join(FormSubmission)
            .filter(
                FormSubmission.submitted_by == username,
                AnswerSubmitted.is_deleted == False,
                FormSubmission.is_deleted == False
            )
            .options(
                joinedload(AnswerSubmitted.form_answer)
                    .joinedload(FormAnswer.answer)
            )
            .all())

    @staticmethod
    def get_submission_statistics(submission_id: int) -> Optional[dict]:
        """Get statistics for a form submission"""
        try:
            submitted_answers = (AnswerSubmitted.query
                .filter_by(
                    form_submissions_id=submission_id,
                    is_deleted=False
                )
                .options(
                    joinedload(AnswerSubmitted.form_answer)
                        .joinedload(FormAnswer.form_question)
                        .joinedload(FormQuestion.question)
                        .joinedload(Question.question_type)
                )
                .all())

            return {
                'total_answers': len(submitted_answers),
                'submission_time': (submitted_answers[0].form_submission.submitted_at 
                                  if submitted_answers else None),
                'has_remarks': any(sa.form_answer.remarks for sa in submitted_answers),
                'answer_types': [
                    sa.form_answer.form_question.question.question_type.type 
                    for sa in submitted_answers
                ]
            }

        except Exception as e:
            logger.error(f"Error getting submission statistics: {str(e)}")
            return None