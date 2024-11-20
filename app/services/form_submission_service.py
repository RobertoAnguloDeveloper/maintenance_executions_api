from typing import Optional, Union
from app import db
from app.models.form import Form
from app.models.form_submission import FormSubmission
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.attachment import Attachment
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging

from app.models.user import User

logger = logging.getLogger(__name__)

class FormSubmissionService:
    @staticmethod
    def create_submission(form_id: int, username: str) -> tuple:
        """Create a new form submission with answers and attachments"""
        try:
            # Start transaction
            db.session.begin_nested()
            
            # Verify form exists
            form = Form.query.get(form_id)
            if not form:
                return None, "Form not found"

            # Create submission
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()

            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating submission: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_all_submissions(filters: dict = None) -> list:
        """
        Get all submissions with optional filters
        
        Args:
            filters (dict): Optional filters including:
                - form_id (int): Filter by specific form
                - start_date (datetime): Filter by start date
                - end_date (datetime): Filter by end date
                - environment_id (int): Filter by environment
                - submitted_by (str): Filter by submitter
        """
        try:
            query = FormSubmission.query.filter_by(is_deleted=False)

            # Apply filters
            if filters:
                if filters.get('form_id'):
                    query = query.filter(FormSubmission.form_id == filters['form_id'])
                
                if filters.get('start_date'):
                    query = query.filter(FormSubmission.submitted_at >= filters['start_date'])
                    
                if filters.get('end_date'):
                    query = query.filter(FormSubmission.submitted_at <= filters['end_date'])
                    
                if filters.get('submitted_by'):
                    query = query.filter(FormSubmission.submitted_by == filters['submitted_by'])
                    
                if filters.get('environment_id'):
                    query = query.join(Form).join(User).filter(
                        User.environment_id == filters['environment_id']
                    )

            # Order by submission date
            query = query.order_by(FormSubmission.submitted_at.desc())
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting submissions: {str(e)}")
            return []

    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        """Get non-deleted submission with relationships"""
        return (FormSubmission.query
            .filter_by(
                id=submission_id,
                is_deleted=False
            )
            .options(
                joinedload(FormSubmission.form)
                    .joinedload(Form.creator),
                joinedload(FormSubmission.answers_submitted)
                    .joinedload(AnswerSubmitted.form_answer)
                    .joinedload(FormAnswer.answer),
                joinedload(FormSubmission.attachments)
            )
            .first())

    @staticmethod
    def get_submissions_by_form(form_id: int) -> list[FormSubmission]:
        """Get all non-deleted submissions for a form"""
        return (FormSubmission.query
            .filter_by(
                form_id=form_id,
                is_deleted=False
            )
            .options(
                joinedload(FormSubmission.answers_submitted),
                joinedload(FormSubmission.attachments)
            )
            .order_by(FormSubmission.submitted_at.desc())
            .all())

    @staticmethod
    def get_submissions_by_user(
        username: str,
        form_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[FormSubmission]:
        """Get submissions by username with optional filters"""
        query = FormSubmission.query.filter_by(
            submitted_by=username,
            is_deleted=False
        )
        
        if form_id:
            query = query.filter_by(form_id=form_id)
            
        if start_date:
            query = query.filter(FormSubmission.submitted_at >= start_date)
            
        if end_date:
            query = query.filter(FormSubmission.submitted_at <= end_date)
            
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_by_environment(
        environment_id: int,
        form_id: Optional[int] = None
    ) -> list[FormSubmission]:
        """Get all non-deleted submissions for an environment"""
        query = (FormSubmission.query
            .join(Form)
            .join(User)
            .filter(
                User.environment_id == environment_id,
                FormSubmission.is_deleted == False,
                Form.is_deleted == False,
                User.is_deleted == False
            ))
            
        if form_id:
            query = query.filter(FormSubmission.form_id == form_id)
            
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def update_submission(submission_id, answers_data=None, attachments_data=None):
        """
        Update a submission's answers and attachments
        """
        try:
            submission = FormSubmission.query.get(submission_id)
            if not submission:
                return None, "Submission not found"

            if answers_data:
                # Remove existing answers
                AnswerSubmitted.query.filter_by(form_submission_id=submission_id).delete()
                
                # Add new answers
                for answer_data in answers_data:
                    form_answer = FormAnswer.query.filter_by(
                        form_question_id=answer_data['form_question_id'],
                        answer_id=answer_data['answer_id']
                    ).first()

                    if not form_answer:
                        form_answer = FormAnswer(
                            form_question_id=answer_data['form_question_id'],
                            answer_id=answer_data['answer_id'],
                            remarks=answer_data.get('remarks')
                        )
                        db.session.add(form_answer)
                        db.session.flush()

                    answer_submitted = AnswerSubmitted(
                        form_answer_id=form_answer.id,
                        form_submission_id=submission_id
                    )
                    db.session.add(answer_submitted)

            if attachments_data:
                # Handle attachments update
                Attachment.query.filter_by(form_submission_id=submission_id).delete()
                
                for attachment_data in attachments_data:
                    attachment = Attachment(
                        form_submission_id=submission_id,
                        file_type=attachment_data['file_type'],
                        file_path=attachment_data['file_path'],
                        is_signature=attachment_data.get('is_signature', False)
                    )
                    db.session.add(attachment)

            submission.updated_at = datetime.utcnow()
            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating submission {submission_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_submission(submission_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a submission and associated data through cascade soft delete
        
        Args:
            submission_id (int): ID of the submission to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return False, "Submission not found"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'answers_submitted': 0,
                'attachments': 0
            }

            # 1. Soft delete submitted answers
            submitted_answers = AnswerSubmitted.query.filter_by(
                form_submissions_id=submission_id,
                is_deleted=False
            ).all()

            for submitted in submitted_answers:
                submitted.soft_delete()
                deletion_stats['answers_submitted'] += 1

            # 2. Soft delete attachments
            attachments = Attachment.query.filter_by(
                form_submission_id=submission_id,
                is_deleted=False
            ).all()

            for attachment in attachments:
                attachment.soft_delete()
                deletion_stats['attachments'] += 1

            # Finally soft delete the submission
            submission.soft_delete()

            # Commit all changes
            db.session.commit()
            
            logger.info(f"Submission {submission_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting submission: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def get_submission_statistics(form_id=None, environment_id=None, date_range=None):
        """Get submission statistics with optional filters"""
        try:
            query = FormSubmission.query

            if form_id:
                query = query.filter_by(form_id=form_id)
            if environment_id:
                query = query.join(FormSubmission.form)\
                    .filter_by(environment_id=environment_id)
            if date_range:
                query = query.filter(
                    FormSubmission.submitted_at.between(
                        date_range['start'],
                        date_range['end']
                    )
                )

            submissions = query.all()
            
            stats = {
                'total_submissions': len(submissions),
                'submissions_by_user': {},
                'submissions_by_date': {},
                'average_answers_per_submission': 0,
                'attachment_stats': {
                    'total_attachments': 0,
                    'submissions_with_attachments': 0
                }
            }

            if submissions:
                # Calculate user statistics
                for submission in submissions:
                    # User stats
                    stats['submissions_by_user'][submission.submitted_by] = \
                        stats['submissions_by_user'].get(submission.submitted_by, 0) + 1

                    # Date stats
                    date_key = submission.submitted_at.date().isoformat()
                    stats['submissions_by_date'][date_key] = \
                        stats['submissions_by_date'].get(date_key, 0) + 1

                    # Attachment stats
                    if submission.attachments:
                        stats['attachment_stats']['total_attachments'] += len(submission.attachments)
                        stats['attachment_stats']['submissions_with_attachments'] += 1

                # Calculate averages
                total_answers = sum(len(s.answers_submitted) for s in submissions)
                stats['average_answers_per_submission'] = total_answers / len(submissions)

            return stats

        except Exception as e:
            logger.error(f"Error calculating submission statistics: {str(e)}")
            return None