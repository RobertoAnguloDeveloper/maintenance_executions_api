from app import db
from app.models.attachment import Attachment
from sqlalchemy.exc import IntegrityError
import logging
import os
from werkzeug.utils import secure_filename
from datetime import datetime

logger = logging.getLogger(__name__)

class AttachmentService:
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'xlsx', 'xls'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
    
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in AttachmentService.ALLOWED_EXTENSIONS

    @staticmethod
    def create_attachment(form_submission_id, file_type, file_path, file_name, file_size, is_signature=False):
        """Create a new attachment"""
        try:
            # Validate file size
            if file_size > AttachmentService.MAX_FILE_SIZE:
                return None, "File size exceeds maximum limit"

            # Validate file type
            if not AttachmentService.allowed_file(file_name):
                return None, "File type not allowed"

            # Secure the filename
            secure_name = secure_filename(file_name)
            
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
            logger.error(f"Integrity error creating attachment: {str(e)}")
            return None, "Invalid form submission ID"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating attachment: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_attachment(attachment_id):
        """Get a specific attachment"""
        return Attachment.query.get(attachment_id)

    @staticmethod
    def get_attachments_by_submission(form_submission_id):
        """Get all attachments for a form submission"""
        return Attachment.query.filter_by(form_submission_id=form_submission_id)\
            .order_by(Attachment.created_at).all()

    @staticmethod
    def get_signature_attachment(form_submission_id):
        """Get signature attachment for a form submission"""
        return Attachment.query.filter_by(
            form_submission_id=form_submission_id,
            is_signature=True
        ).first()

    @staticmethod
    def update_attachment(attachment_id, **kwargs):
        """Update an attachment's details"""
        try:
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return None, "Attachment not found"

            # Update allowed fields
            allowed_fields = ['file_type', 'file_path', 'is_signature']
            for key, value in kwargs.items():
                if key in allowed_fields:
                    setattr(attachment, key, value)

            attachment.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Updated attachment {attachment_id}")
            return attachment, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating attachment {attachment_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_attachment(attachment_id):
        """Delete an attachment and its associated file"""
        try:
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return False, "Attachment not found"

            # Delete the physical file if it exists
            if os.path.exists(attachment.file_path):
                try:
                    os.remove(attachment.file_path)
                except OSError as e:
                    logger.error(f"Error deleting file {attachment.file_path}: {str(e)}")

            db.session.delete(attachment)
            db.session.commit()
            
            logger.info(f"Deleted attachment {attachment_id}")
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_attachments_stats(form_submission_id=None):
        """Get attachment statistics"""
        try:
            query = Attachment.query
            if form_submission_id:
                query = query.filter_by(form_submission_id=form_submission_id)

            attachments = query.all()
            
            stats = {
                'total_attachments': len(attachments),
                'by_type': {},
                'signatures_count': sum(1 for a in attachments if a.is_signature),
                'types_distribution': {},
            }

            for attachment in attachments:
                stats['by_type'][attachment.file_type] = \
                    stats['by_type'].get(attachment.file_type, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"Error getting attachment statistics: {str(e)}")
            return None