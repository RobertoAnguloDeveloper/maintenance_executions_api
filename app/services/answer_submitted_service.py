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
from app.models.question_type import QuestionType
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
        """Get all answers submitted with filters"""
        try:
            query = AnswerSubmitted.query.filter_by(is_deleted=False)

            if filters:
                if filters.get('form_id'):
                    query = (query
                        .join(
                            FormSubmission,
                            FormSubmission.id == AnswerSubmitted.form_submissions_id
                        )
                        .filter(
                            FormSubmission.form_id == filters['form_id'],
                            FormSubmission.is_deleted == False
                        ))
                        
                if filters.get('environment_id'):
                    query = (query
                        .join(
                            FormSubmission,
                            FormSubmission.id == AnswerSubmitted.form_submissions_id
                        )
                        .join(
                            Form,
                            Form.id == FormSubmission.form_id
                        )
                        .join(
                            User,
                            User.id == Form.user_id
                        )
                        .filter(
                            User.environment_id == filters['environment_id'],
                            FormSubmission.is_deleted == False,
                            Form.is_deleted == False,
                            User.is_deleted == False
                        ))

                # Add date range filters with proper join validation
                if filters.get('start_date'):
                    query = query.join(
                        FormSubmission,
                        FormSubmission.id == AnswerSubmitted.form_submissions_id
                    ).filter(
                        FormSubmission.submitted_at >= filters['start_date'],
                        FormSubmission.is_deleted == False
                    )
                    
                if filters.get('end_date'):
                    query = query.join(
                        FormSubmission,
                        FormSubmission.id == AnswerSubmitted.form_submissions_id
                    ).filter(
                        FormSubmission.submitted_at <= filters['end_date'],
                        FormSubmission.is_deleted == False
                    )

            # Add proper eager loading with soft delete checks
            query = query.options(
                joinedload(AnswerSubmitted.form_answer)
                    .filter(FormAnswer.is_deleted == False)
                    .joinedload(FormAnswer.form_question)
                    .filter(FormQuestion.is_deleted == False)
                    .joinedload(FormQuestion.question)
                    .filter(Question.is_deleted == False),
                joinedload(AnswerSubmitted.form_submission)
                    .filter(FormSubmission.is_deleted == False)
            )

            return query.order_by(AnswerSubmitted.created_at.desc()).all()

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
        Permanently delete a submitted answer
        
        Args:
            answer_submitted_id (int): ID of the submitted answer to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                result contains either deletion statistics or error message
        """
        try:
            answer_submitted = AnswerSubmitted.query.get(answer_submitted_id)
            
            if not answer_submitted:
                return False, "Submitted answer not found"

            # Start transaction
            db.session.begin_nested()

            # Perform hard delete
            db.session.delete(answer_submitted)
            db.session.commit()
            
            logger.info(f"Submitted answer {answer_submitted_id} permanently deleted")
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
                        .filter(FormAnswer.is_deleted == False)
                        .joinedload(FormAnswer.form_question)
                        .filter(FormQuestion.is_deleted == False)
                        .joinedload(FormQuestion.question)
                        .filter(Question.is_deleted == False)
                        .joinedload(Question.question_type)
                        .filter(QuestionType.is_deleted == False)
                )
                .all())

            if not submitted_answers:
                return None

            return {
                'total_answers': len(submitted_answers),
                'submission_time': (submitted_answers[0].form_submission.submitted_at 
                                if not submitted_answers[0].form_submission.is_deleted else None),
                'has_remarks': any(sa.form_answer.remarks for sa in submitted_answers 
                                if not sa.form_answer.is_deleted),
                'answer_types': [
                    sa.form_answer.form_question.question.question_type.type 
                    for sa in submitted_answers 
                    if not sa.form_answer.is_deleted and 
                    not sa.form_answer.form_question.is_deleted and
                    not sa.form_answer.form_question.question.is_deleted and
                    not sa.form_answer.form_question.question.question_type.is_deleted
                ]
            }

        except Exception as e:
            logger.error(f"Error getting submission statistics: {str(e)}")
            return None