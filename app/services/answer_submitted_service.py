# app/services/answer_submitted_service.py

from app import db
from app.models.answers_submitted import AnswerSubmitted
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.models.form import Form
from app.models.form_submission import FormSubmission
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
    def get_answer_submitted(answer_submitted_id):
        """Get a specific submitted answer"""
        return AnswerSubmitted.query.filter_by(id=answer_submitted_id, is_deleted=False).first()

    @staticmethod
    def get_answers_by_submission(submission_id, include_deleted=False):
        """Get submitted answers for a submission"""
        query = AnswerSubmitted.query.filter_by(form_submission_id=submission_id, is_deleted=False)
        
        if not include_deleted:
            query = query.filter(AnswerSubmitted.is_deleted == False)
            
        return query.order_by(AnswerSubmitted.created_at).all()

    @staticmethod
    def delete_answer_submitted(answer_submitted_id):
        """Soft delete a submitted answer"""
        try:
            answer_submitted = AnswerSubmitted.query.get(answer_submitted_id)
            if not answer_submitted:
                return False, "Submitted answer not found"

            answer_submitted.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_answers_by_user(username):
        """Get all submitted answers for a specific user"""
        return (AnswerSubmitted.query
                .join(AnswerSubmitted.form_submission)
                .filter_by(submitted_by=username, is_deleted=False)
                .all())

    @staticmethod
    def get_submission_statistics(submission_id):
        """Get statistics for a form submission"""
        try:
            submitted_answers = AnswerSubmitted.query\
                .filter_by(form_submission_id=submission_id, is_deleted=False)\
                .all()

            return {
                'total_answers': len(submitted_answers),
                'submission_time': submitted_answers[0].form_submission.submitted_at if submitted_answers else None,
                'has_remarks': any(sa.form_answer.remarks for sa in submitted_answers),
                'answer_types': [sa.form_answer.form_question.question.question_type.type for sa in submitted_answers]
            }

        except Exception as e:
            return None