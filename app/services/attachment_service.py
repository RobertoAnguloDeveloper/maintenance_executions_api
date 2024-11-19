from app import db
from app.models.attachment import Attachment
from sqlalchemy.exc import IntegrityError
import logging
import os
from werkzeug.utils import secure_filename
from datetime import datetime

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
    def get_attachment(attachment_id: int) -> Attachment:
        """Get a specific attachment"""
        return Attachment.query.get(attachment_id)

    @staticmethod
    def get_attachments_by_submission(form_submission_id: int, include_deleted: bool = False) -> list:
        """Get all attachments for a submission"""
        query = Attachment.query.filter_by(form_submission_id=form_submission_id)
        
        if not include_deleted:
            query = query.filter(Attachment.is_deleted == False)
            
        return query.order_by(Attachment.created_at).all()

    @staticmethod
    def get_signature_attachment(form_submission_id: int) -> Attachment:
        """Get signature attachment for a submission"""
        return Attachment.query.filter_by(
            form_submission_id=form_submission_id,
            is_signature=True,
            is_deleted=False
        ).first()

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
    def delete_attachment(attachment_id: int) -> tuple:
        """Soft delete an attachment"""
        try:
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return False, "Attachment not found"

            attachment.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_attachments_stats(form_submission_id: int = None) -> dict:
        """Get attachment statistics"""
        try:
            query = Attachment.query
            if form_submission_id:
                query = query.filter_by(form_submission_id=form_submission_id)

            attachments = query.filter_by(is_deleted=False).all()
            
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