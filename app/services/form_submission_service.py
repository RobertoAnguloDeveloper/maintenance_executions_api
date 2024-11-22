from typing import Optional, Union, List, Dict, Any
from app import db
from app.models.answer import Answer
from app.models.form import Form
from app.models.form_question import FormQuestion
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
        try:
            query = (FormSubmission.query
                .join(Form, Form.id == FormSubmission.form_id)
                .join(User, User.id == Form.user_id)
                .filter(
                    User.environment_id == environment_id,
                    FormSubmission.is_deleted == False,
                    Form.is_deleted == False,
                    User.is_deleted == False
                )
                .options(
                    joinedload(FormSubmission.answers_submitted)
                        .filter(AnswerSubmitted.is_deleted == False)
                        .joinedload(AnswerSubmitted.form_answer)
                        .filter(FormAnswer.is_deleted == False),
                    joinedload(FormSubmission.attachments)
                        .filter(Attachment.is_deleted == False)
                ))
                
            if form_id:
                query = query.filter(FormSubmission.form_id == form_id)
                
            return query.order_by(FormSubmission.submitted_at.desc()).all()

        except Exception as e:
            logger.error(f"Error getting submissions by environment: {str(e)}")
            return []

    @staticmethod
    def update_submission(
        submission_id: int,
        answers_data: Optional[List[Dict[str, Any]]] = None,
        attachments_data: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[Optional[FormSubmission], Optional[str]]:
        """
        Update a form submission with new answers and attachments.
        
        Args:
            submission_id: ID of the submission to update
            answers_data: List of answer data dictionaries
            attachments_data: List of attachment data dictionaries
            
        Returns:
            tuple: (Updated FormSubmission object or None, Error message or None)
        """
        try:
            # Verify submission exists and is not deleted
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return None, "Submission not found or has been deleted"

            # Start transaction
            db.session.begin_nested()

            if answers_data:
                # Validate all answers before making any changes
                for answer_data in answers_data:
                    # Verify form question exists and is not deleted
                    form_question = FormQuestion.query.filter_by(
                        id=answer_data.get('form_question_id'),
                        is_deleted=False
                    ).first()
                    
                    if not form_question:
                        db.session.rollback()
                        return None, f"Form question {answer_data.get('form_question_id')} not found or has been deleted"

                    # Verify form question belongs to the submission's form
                    if form_question.form_id != submission.form_id:
                        db.session.rollback()
                        return None, f"Form question {form_question.id} does not belong to this form"

                    # Verify answer exists and is not deleted
                    answer = Answer.query.filter_by(
                        id=answer_data.get('answer_id'),
                        is_deleted=False
                    ).first()
                    
                    if not answer:
                        db.session.rollback()
                        return None, f"Answer {answer_data.get('answer_id')} not found or has been deleted"

                # Soft delete existing answers
                existing_submissions = AnswerSubmitted.query.filter_by(
                    form_submissions_id=submission_id,
                    is_deleted=False
                ).all()
                
                for existing in existing_submissions:
                    existing.is_deleted = True
                    existing.deleted_at = datetime.utcnow()

                # Create new answer submissions
                for answer_data in answers_data:
                    # Get or create form answer
                    form_answer = FormAnswer.query.filter_by(
                        form_question_id=answer_data['form_question_id'],
                        answer_id=answer_data['answer_id'],
                        is_deleted=False
                    ).first()

                    if not form_answer:
                        form_answer = FormAnswer(
                            form_question_id=answer_data['form_question_id'],
                            answer_id=answer_data['answer_id']
                        )
                        db.session.add(form_answer)
                        db.session.flush()

                    # Create new answer submission
                    answer_submitted = AnswerSubmitted(
                        form_answers_id=form_answer.id,
                        form_submissions_id=submission_id
                    )
                    db.session.add(answer_submitted)

            if attachments_data:
                # Validate attachment data
                for attachment_data in attachments_data:
                    if not all(key in attachment_data for key in ['file_type', 'file_path']):
                        db.session.rollback()
                        return None, "Invalid attachment data: missing required fields"

                # Soft delete existing attachments
                existing_attachments = Attachment.query.filter_by(
                    form_submission_id=submission_id,
                    is_deleted=False
                ).all()
                
                for existing in existing_attachments:
                    existing.is_deleted = True
                    existing.deleted_at = datetime.utcnow()

                # Create new attachments
                for attachment_data in attachments_data:
                    attachment = Attachment(
                        form_submission_id=submission_id,
                        file_type=attachment_data['file_type'],
                        file_path=attachment_data['file_path'],
                        is_signature=attachment_data.get('is_signature', False)
                    )
                    db.session.add(attachment)

            # Update submission timestamp
            submission.updated_at = datetime.utcnow()
            
            # Commit all changes
            db.session.commit()
            
            # Refresh submission to load relationships
            db.session.refresh(submission)
            
            logger.info(f"Successfully updated submission {submission_id}")
            return submission, None

        except IntegrityError as e:
            db.session.rollback()
            error_msg = "Database integrity error: possibly invalid relationships"
            logger.error(f"{error_msg}: {str(e)}")
            return None, error_msg
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error updating submission: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def delete_submission(submission_id: int, current_user: User) -> tuple[bool, Union[dict, str]]:
        """
        Delete a submission with cascade soft delete using SoftDeleteMixin.
        
        Args:
            submission_id: ID of the submission to delete
            current_user: Current user object for authorization
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
        """
        try:
            # Get submission checking is_deleted=False
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return False, "Submission not found"

            # Authorization check
            if not current_user.role.is_super_user:
                if current_user.role.name in ['Site Manager', 'Supervisor']:
                    if submission.form.creator.environment_id != current_user.environment_id:
                        return False, "Unauthorized: Submission belongs to different environment"
                elif submission.submitted_by != current_user.username:
                    return False, "Unauthorized: Cannot delete submissions by other users"

            # Check submission age for non-admin users
            if not current_user.role.is_super_user:
                submission_age = datetime.utcnow() - submission.submitted_at
                if submission_age.days > 7:  # Configurable timeframe
                    return False, "Cannot delete submissions older than 7 days"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'answers_submitted': 0,
                'attachments': 0,
                'submissions': 1
            }

            # Soft delete submitted answers using SoftDeleteMixin
            answers_submitted = AnswerSubmitted.query.filter_by(
                form_submissions_id=submission_id,
                is_deleted=False
            ).all()

            for answer in answers_submitted:
                answer.soft_delete()  # Using SoftDeleteMixin method
                deletion_stats['answers_submitted'] += 1

            # Soft delete attachments using SoftDeleteMixin
            attachments = Attachment.query.filter_by(
                form_submission_id=submission_id,
                is_deleted=False
            ).all()

            for attachment in attachments:
                attachment.soft_delete()  # Using SoftDeleteMixin method
                deletion_stats['attachments'] += 1

            # Soft delete the submission using SoftDeleteMixin
            submission.soft_delete()  # Using SoftDeleteMixin method

            # Commit all changes
            db.session.commit()
            
            logger.info(
                f"Submission {submission_id} and associated data deleted by "
                f"{current_user.username}. Stats: {deletion_stats}"
            )
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
            query = FormSubmission.query.filter_by(is_deleted=False)

            if form_id:
                query = query.filter_by(form_id=form_id)
                
            if environment_id:
                query = (query
                    .join(Form, Form.id == FormSubmission.form_id)
                    .join(User, User.id == Form.user_id)
                    .filter(
                        User.environment_id == environment_id,
                        Form.is_deleted == False,
                        User.is_deleted == False
                    ))
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
                'attachment_stats': {
                    'total_attachments': 0,
                    'submissions_with_attachments': 0
                }
            }

            # Only count non-deleted related records
            for submission in submissions:
                # User stats
                stats['submissions_by_user'][submission.submitted_by] = \
                    stats['submissions_by_user'].get(submission.submitted_by, 0) + 1

                # Date stats
                date_key = submission.submitted_at.date().isoformat()
                stats['submissions_by_date'][date_key] = \
                    stats['submissions_by_date'].get(date_key, 0) + 1

                # Attachment stats
                active_attachments = [a for a in submission.attachments if not a.is_deleted]
                if active_attachments:
                    stats['attachment_stats']['total_attachments'] += len(active_attachments)
                    stats['attachment_stats']['submissions_with_attachments'] += 1

            return stats

        except Exception as e:
            logger.error(f"Error calculating submission statistics: {str(e)}")
            return None