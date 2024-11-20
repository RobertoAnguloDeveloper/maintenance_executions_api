from typing import Optional, Union
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

logger = logging.getLogger(__name__)

class AttachmentService:
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    @staticmethod
    def create_attachment(form_submission_id: int, file_type: str, file_path: str, 
                         file_name: str, is_signature: bool = False) -> tuple:
        """Create a new attachment"""
        try:
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

        except IntegrityError:
            db.session.rollback()
            logger.error("Invalid form submission ID")
            return None, "Invalid form submission ID"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating attachment: {str(e)}")
            return None, str(e)

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
    def update_attachment(attachment_id: int, **kwargs) -> tuple:
        """Update an attachment"""
        try:
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return None, "Attachment not found"

            for key, value in kwargs.items():
                if hasattr(attachment, key):
                    setattr(attachment, key, value)

            db.session.commit()
            return attachment, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating attachment: {str(e)}")
            return None, str(e)

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
    def get_attachments_stats(form_submission_id: Optional[int] = None) -> Optional[dict]:
        """Get attachment statistics"""
        try:
            query = Attachment.query.filter_by(is_deleted=False)
            
            if form_submission_id:
                query = query.filter_by(form_submission_id=form_submission_id)

            attachments = query.all()
            
            return {
                'total_attachments': len(attachments),
                'by_type': {
                    file_type: len([a for a in attachments if a.file_type == file_type])
                    for file_type in set(a.file_type for a in attachments)
                },
                'signatures_count': len([a for a in attachments if a.is_signature]),
            }

        except Exception as e:
            logger.error(f"Error getting attachment statistics: {str(e)}")
            return None