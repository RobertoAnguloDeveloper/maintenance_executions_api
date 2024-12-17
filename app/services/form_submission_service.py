from typing import Dict, List, Optional, Tuple
from app import db
from app.models.form_submission import FormSubmission
from app.models.answer_submitted import AnswerSubmitted
from app.utils.permission_manager import RoleType
from app.models.attachment import Attachment
from app.models.form import Form
from sqlalchemy.orm import joinedload
from datetime import datetime
import logging
import os

from app.models.user import User

logger = logging.getLogger(__name__)

class FormSubmissionService:
    @staticmethod
    def create_submission(
        form_id: int,
        username: str,
        answers_data: List[Dict] = None,
        upload_path: Optional[str] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Create a new form submission with answers and handle signatures
        
        Args:
            form_id: ID of the form being submitted
            username: Username of the submitter
            answers_data: List of answer data dictionaries
            upload_path: Base path for file uploads
            
        Returns:
            tuple: (Created FormSubmission object or None, Error message or None)
        """
        try:
            # Verify form exists and is active
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found or inactive"

            # Create submission
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()

            # Process answers if provided
            if answers_data:
                for answer_data in answers_data:
                    # Create answer submission
                    answer = AnswerSubmitted(
                        form_submission_id=submission.id,
                        question=answer_data['question_text'],
                        answer=answer_data['answer_text']
                    )
                    db.session.add(answer)

                    # Handle signature if required
                    if answer_data.get('is_signature') and answer_data.get('signature_file'):
                        if not upload_path:
                            return None, "Upload path not provided for signature file"

                        # Create signature directory
                        signature_dir = os.path.join(upload_path, 'signatures', str(submission.id))
                        os.makedirs(signature_dir, exist_ok=True)

                        # Save signature file
                        signature_file = answer_data['signature_file']
                        filename = f"signature_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(signature_file.filename)[1]}"
                        file_path = os.path.join('signatures', str(submission.id), filename)
                        signature_file.save(os.path.join(upload_path, file_path))

                        # Create attachment record
                        attachment = Attachment(
                            form_submission_id=submission.id,
                            file_type=signature_file.content_type,
                            file_path=file_path,
                            is_signature=True
                        )
                        db.session.add(attachment)

            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form submission: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_all_submissions(user: User, filters: Optional[Dict] = None) -> List[FormSubmission]:
        """
        Get all form submissions with role-based filtering and access control.
        
        Args:
            user: Current user object for role-based access
            filters: Optional dictionary containing filters:
                - form_id: Filter by specific form
                - date_range: Dict with 'start' and 'end' dates
                - environment_id: Filter by environment
                - submitted_by: Filter by submitter username
                
        Returns:
            List[FormSubmission]: List of form submissions matching criteria
        """
        try:
            # Base query with proper joins and filters
            query = (FormSubmission.query
                .join(Form)
                .filter(
                    FormSubmission.is_deleted == False,
                    Form.is_deleted == False
                ))
            
            # Apply role-based filtering
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Can only see submissions in their environment
                    query = (query
                        .join(User, User.id == Form.user_id)
                        .filter(User.environment_id == user.environment_id))
                else:
                    # Regular users can only see their own submissions
                    query = query.filter(FormSubmission.submitted_by == user.username)

            # Apply optional filters
            if filters:
                if 'form_id' in filters:
                    query = query.filter(FormSubmission.form_id == filters['form_id'])
                    
                if 'environment_id' in filters:
                    query = (query
                        .join(User, User.id == Form.user_id)
                        .filter(User.environment_id == filters['environment_id']))
                        
                if 'submitted_by' in filters:
                    query = query.filter(
                        FormSubmission.submitted_by == filters['submitted_by']
                    )
                    
                if 'date_range' in filters:
                    date_range = filters['date_range']
                    if date_range.get('start'):
                        query = query.filter(
                            FormSubmission.submitted_at >= date_range['start']
                        )
                    if date_range.get('end'):
                        query = query.filter(
                            FormSubmission.submitted_at <= date_range['end']
                        )

            # Add eager loading for related data
            query = (query.options(
                joinedload(FormSubmission.form),
                joinedload(FormSubmission.answers_submitted),
                joinedload(FormSubmission.attachments)
            ))

            # Order by submission date, most recent first
            submissions = query.order_by(FormSubmission.submitted_at.desc()).all()
            
            return submissions

        except Exception as e:
            logger.error(f"Error getting submissions: {str(e)}")
            return []

    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        """
        Get a specific form submission with all related data
        
        Args:
            submission_id: ID of the submission
            
        Returns:
            Optional[FormSubmission]: FormSubmission object if found, None otherwise
        """
        try:
            return (FormSubmission.query
                .filter_by(
                    id=submission_id,
                    is_deleted=False
                )
                .options(
                    joinedload(FormSubmission.form),
                    joinedload(FormSubmission.answers_submitted),
                    joinedload(FormSubmission.attachments)
                )
                .first())
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_id}: {str(e)}")
            return None
        
    @staticmethod
    def get_submissions_by_user(username: str, filters: Dict = None) -> List[FormSubmission]:
        """
        Get all submissions for a specific user with optional filtering.
        
        Args:
            username: Username of the submitter
            filters: Optional dictionary containing filters
                - start_date: Start date for filtering
                - end_date: End date for filtering
                - form_id: Filter by specific form
                
        Returns:
            List[FormSubmission]: List of form submissions
        """
        try:
            query = FormSubmission.query.filter_by(
                submitted_by=username,
                is_deleted=False
            )

            if filters:
                if 'start_date' in filters:
                    query = query.filter(FormSubmission.submitted_at >= filters['start_date'])
                if 'end_date' in filters:
                    query = query.filter(FormSubmission.submitted_at <= filters['end_date'])
                if 'form_id' in filters:
                    query = query.filter_by(form_id=filters['form_id'])

            return query.order_by(FormSubmission.submitted_at.desc()).all()

        except Exception as e:
            logger.error(f"Error getting submissions for user {username}: {str(e)}")
            return []

    @staticmethod
    def delete_submission(submission_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a submission with cascade soft delete
        
        Args:
            submission_id: ID of the submission to delete
            
        Returns:
            tuple: (Success boolean, Error message or None)
        """
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return False, "Submission not found"

            # Start transaction for cascade soft delete
            db.session.begin_nested()

            # Soft delete answers
            for answer in submission.answers_submitted:
                if not answer.is_deleted:
                    answer.soft_delete()

            # Soft delete attachments
            for attachment in submission.attachments:
                if not attachment.is_deleted:
                    attachment.soft_delete()

            # Finally soft delete the submission
            submission.soft_delete()
            
            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting submission: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_submission_answers(submission_id: int) -> Tuple[List[Dict], Optional[str]]:
        """Get all answers for a specific submission"""
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return [], "Submission not found"

            answers = []
            for answer in submission.answers_submitted:
                if not answer.is_deleted:
                    answer_dict = answer.to_dict()
                    # Add signature info if available
                    signature = next((att for att in submission.attachments 
                                   if att.is_signature and not att.is_deleted), None)
                    if signature:
                        answer_dict['signature'] = signature.to_dict()
                    answers.append(answer_dict)

            return answers, None

        except Exception as e:
            logger.error(f"Error getting submission answers: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_submission_status(
        submission_id: int,
        status: str
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """Update submission status"""
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return None, "Submission not found"

            # Update status and timestamps
            submission.status = status
            submission.updated_at = datetime.utcnow()
            
            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating submission status: {str(e)}")
            return None, str(e)