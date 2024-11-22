from typing import Any, Dict, Optional, Tuple, Union
from app import db
from flask import current_app
from app.models.attachment import Attachment
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging
import os
from werkzeug.utils import secure_filename
from datetime import datetime

from app.models.form import Form
from app.models.form_submission import FormSubmission
from app.models.user import User

logger = logging.getLogger(__name__)

class AttachmentService:
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    @staticmethod
    def create_attachment(
        form_submission_id: int,
        file_type: str,
        file_path: str,
        file_name: str,
        file_size: int,
        is_signature: bool = False,
        current_user: User = None
    ) -> Tuple[Optional[Attachment], Optional[str]]:
        """
        Create a new attachment with validation and soft-delete checks.
        
        Args:
            form_submission_id: ID of the form submission
            file_type: MIME type of the file
            file_path: Path where file is stored
            file_name: Original name of the file
            file_size: Size of the file in bytes
            is_signature: Whether this is a signature file
            current_user: Current user object for additional validation
            
        Returns:
            tuple: (Created Attachment object or None, Error message or None)
        """
        try:
            # Verify form submission exists and is not deleted
            submission = FormSubmission.query.filter_by(
                id=form_submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return None, "Form submission not found or has been deleted"

            # Additional validation for submission ownership if user provided
            if current_user and not current_user.role.is_super_user:
                if submission.submitted_by != current_user.username:
                    if current_user.role.name not in ['Site Manager', 'Supervisor']:
                        return None, "Unauthorized: Cannot create attachment for this submission"
                    elif submission.form.creator.environment_id != current_user.environment_id:
                        return None, "Unauthorized: Submission belongs to different environment"

            # Validate file extension
            if not AttachmentService._is_allowed_file(file_name):
                return None, f"File type not allowed. Allowed types: {', '.join(AttachmentService.ALLOWED_EXTENSIONS)}"

            # Validate file size
            if file_size > AttachmentService.MAX_FILE_SIZE:
                return None, f"File size exceeds limit of {AttachmentService.MAX_FILE_SIZE / (1024*1024)}MB"

            # Start transaction
            db.session.begin_nested()

            # If this is a signature, soft delete any existing signature
            if is_signature:
                existing_signatures = Attachment.query.filter_by(
                    form_submission_id=form_submission_id,
                    is_signature=True,
                    is_deleted=False
                ).all()
                
                for existing in existing_signatures:
                    existing.is_deleted = True
                    existing.deleted_at = datetime.utcnow()

            # Create new attachment
            new_attachment = Attachment(
                form_submission_id=form_submission_id,
                file_type=file_type,
                file_path=file_path,
                is_signature=is_signature
            )
            db.session.add(new_attachment)
            db.session.commit()

            logger.info(f"Created attachment for submission {form_submission_id}")
            return new_attachment, None

        except IntegrityError as e:
            db.session.rollback()
            error_msg = "Database integrity error: possibly invalid form submission ID"
            logger.error(f"{error_msg}: {str(e)}")
            return None, error_msg
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error creating attachment: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def get_attachment(attachment_id: int) -> Optional[Attachment]:
        """Get non-deleted attachment with relationships"""
        return (Attachment.query
            .filter_by(
                id=attachment_id,
                is_deleted=False
            )
            .options(
                joinedload(Attachment.form_submission)
                    .joinedload(FormSubmission.form)
                    .joinedload(Form.creator)
            )
            .first())

    @staticmethod
    def get_attachments_by_submission(
        form_submission_id: int,
        include_deleted: bool = False
    ) -> list[Attachment]:
        """Get attachments for a submission"""
        query = Attachment.query.filter_by(
            form_submission_id=form_submission_id
        )
        
        if not include_deleted:
            query = query.filter(Attachment.is_deleted == False)
            
        return query.order_by(Attachment.created_at).all()

    @staticmethod
    def get_signature_attachment(form_submission_id: int) -> tuple[Optional[Attachment], Optional[str]]:
        """Get signature attachment for a submission"""
        try:
            attachment = Attachment.query.filter_by(
                form_submission_id=form_submission_id,
                is_signature=True,
                is_deleted=False
            ).first()
            
            if not attachment:
                return None, "Signature attachment not found"
                
            return attachment, None
            
        except Exception as e:
            error_msg = f"Error getting signature attachment: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        
    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """Validate file before processing"""
        try:
            if not filename:
                return False, "No filename provided"

            # Check file extension
            if '.' not in filename:
                return False, "No file extension provided"

            if filename.rsplit('.', 1)[1].lower() not in AttachmentService.ALLOWED_EXTENSIONS:
                return False, (
                    f"File type not allowed. Allowed types: "
                    f"{', '.join(AttachmentService.ALLOWED_EXTENSIONS)}"
                )

            # Check file size (16MB limit)
            if file_size > 16 * 1024 * 1024:
                return False, "File size exceeds 16MB limit"

            return True, None
            
        except Exception as e:
            error_msg = f"Error validating file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def update_attachment(
        attachment_id: int,
        current_user: User,
        **kwargs
    ) -> Tuple[Optional[Attachment], Optional[str]]:
        """
        Update an attachment with proper validation and soft-delete checks.
        
        Args:
            attachment_id: ID of the attachment to update
            current_user: Current user object for authorization
            **kwargs: Fields to update (file_type, is_signature)
            
        Returns:
            tuple: (Updated Attachment object or None, Error message or None)
        """
        try:
            # Verify attachment exists and is not deleted
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).first()
            
            if not attachment:
                return None, "Attachment not found or has been deleted"

            # Authorization check
            if not current_user.role.is_super_user:
                submission = attachment.form_submission
                if current_user.role.name in ['Site Manager', 'Supervisor']:
                    if submission.form.creator.environment_id != current_user.environment_id:
                        return None, "Unauthorized: Attachment belongs to different environment"
                elif submission.submitted_by != current_user.username:
                    return None, "Unauthorized: Cannot update this attachment"

            # Validate updateable fields
            allowed_fields = {'file_type', 'is_signature'}
            update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not update_data:
                return None, "No valid fields to update"

            # Start transaction
            db.session.begin_nested()

            # Handle signature updates
            if update_data.get('is_signature'):
                existing_signatures = Attachment.query.filter_by(
                    form_submission_id=attachment.form_submission_id,
                    is_signature=True,
                    is_deleted=False
                ).filter(Attachment.id != attachment_id).all()
                
                for existing in existing_signatures:
                    existing.is_deleted = True
                    existing.deleted_at = datetime.utcnow()

            # Update attachment
            for key, value in update_data.items():
                setattr(attachment, key, value)

            attachment.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Updated attachment {attachment_id}")
            return attachment, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error updating attachment: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def delete_attachment(attachment_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete an attachment and its associated file
        
        Args:
            attachment_id (int): ID of the attachment to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).first()
            
            if not attachment:
                return False, "Attachment not found"

            # Start transaction
            db.session.begin_nested()

            # Get the full file path
            file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                attachment.file_path
            )

            # Delete the physical file if it exists
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")
                    # Continue with soft delete even if file deletion fails
                    
            # Soft delete the attachment record
            attachment.soft_delete()

            # Commit changes
            db.session.commit()
            
            logger.info(f"Attachment {attachment_id} and file soft deleted")
            return True, {
                "attachments": 1,
                "file_deleted": os.path.exists(file_path)
            }

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting attachment: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def get_attachments_stats(
        form_submission_id: Optional[int] = None,
        environment_id: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Get attachment statistics with proper soft-delete handling.
        
        Args:
            form_submission_id: Optional submission ID to filter by
            environment_id: Optional environment ID to filter by
            
        Returns:
            tuple: (Statistics dictionary or None, Error message or None)
        """
        try:
            query = Attachment.query.filter_by(is_deleted=False)

            if form_submission_id:
                query = query.filter_by(form_submission_id=form_submission_id)

            if environment_id:
                query = query.join(
                    FormSubmission,
                    Form,
                    User
                ).filter(
                    User.environment_id == environment_id,
                    User.is_deleted == False,
                    Form.is_deleted == False,
                    FormSubmission.is_deleted == False
                )

            attachments = query.all()

            stats = {
                'total_attachments': len(attachments),
                'by_type': {},
                'total_size': 0,
                'signatures_count': 0
            }

            for attachment in attachments:
                # Count by type
                stats['by_type'][attachment.file_type] = \
                    stats['by_type'].get(attachment.file_type, 0) + 1

                # Count signatures
                if attachment.is_signature:
                    stats['signatures_count'] += 1

            return stats, None

        except Exception as e:
            error_msg = f"Error generating attachment statistics: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        
    @staticmethod
    def _is_allowed_file(filename: str) -> bool:
        """Check if the file extension is allowed."""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in AttachmentService.ALLOWED_EXTENSIONS