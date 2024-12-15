from typing import Dict, List, Optional, Tuple
from app import db
from app.models.form_submission import FormSubmission
from app.models.answer_submitted import AnswerSubmitted
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