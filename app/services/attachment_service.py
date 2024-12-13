from typing import BinaryIO, Optional, Tuple, List
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename
from app import db
from app.models.attachment import Attachment

logger = logging.getLogger(__name__)

class AttachmentService:
    @staticmethod
    def get_unique_filename(upload_path: str, filename: str) -> str:
        """Generate unique filename to avoid overwrites"""
        base_name, extension = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(upload_path, new_filename)):
            new_filename = f"{base_name}_{counter}{extension}"
            counter += 1
            
        return new_filename

    @staticmethod
    def create_file_path(username: str, filename: str) -> str:
        """Create organized file path structure"""
        today = datetime.now()
        return os.path.join(
            username,
            str(today.year),
            str(today.month),
            str(today.day),
            filename
        )

    @staticmethod
    def validate_file(
        file: BinaryIO,
        filename: str,
        max_size: int = None
    ) -> Tuple[bool, Optional[str]]:
        """Comprehensive file validation"""
        try:
            if not filename:
                return False, "No filename provided"

            # Secure filename
            secure_name = secure_filename(filename)
            if not secure_name:
                return False, "Invalid filename"

            # Check extension
            if not Attachment.is_allowed_file(secure_name):
                return False, f"File type not allowed. Allowed types: {', '.join(Attachment.ALLOWED_EXTENSIONS)}"

            # Check file size
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            
            max_size = max_size or Attachment.MAX_FILE_SIZE
            if size > max_size:
                return False, f"File size exceeds limit of {max_size / (1024*1024)}MB"

            # Check MIME type
            file_content = file.read(2048)  # Read first 2048 bytes for MIME check
            file.seek(0)
            is_valid_mime, mime_type = Attachment.is_allowed_mime_type(file_content)
            if not is_valid_mime:
                return False, "Invalid file type"

            return True, None

        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, "Error validating file"

    @staticmethod
    def save_file(
        file: BinaryIO,
        base_path: str,
        file_path: str
    ) -> Tuple[bool, Optional[str]]:
        """Save file with proper error handling"""
        try:
            full_path = os.path.join(base_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            file.save(full_path)
            return True, None
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return False, "Error saving file"

    @staticmethod
    def create_attachment(
        form_submission_id: int,
        file: BinaryIO,
        filename: str,
        username: str,
        upload_path: str,
        is_signature: bool = False
    ) -> Tuple[Optional[Attachment], Optional[str]]:
        """Create new attachment with enhanced validation"""
        try:
            # Validate file
            is_valid, error = AttachmentService.validate_file(file, filename)
            if not is_valid:
                return None, error

            secure_name = secure_filename(filename)
            unique_name = AttachmentService.get_unique_filename(upload_path, secure_name)
            file_path = AttachmentService.create_file_path(username, unique_name)

            # Save file
            success, error = AttachmentService.save_file(file, upload_path, file_path)
            if not success:
                return None, error

            # Create database record
            file_content = file.read(2048)
            file.seek(0)
            _, mime_type = Attachment.is_allowed_mime_type(file_content)

            attachment = Attachment(
                form_submission_id=form_submission_id,
                file_type=mime_type,
                file_path=file_path,
                is_signature=is_signature
            )
            
            db.session.add(attachment)
            db.session.commit()
            
            return attachment, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating attachment: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_attachment(
        attachment_id: int,
        base_path: str
    ) -> Tuple[bool, Optional[str]]:
        """Delete attachment with file cleanup"""
        try:
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return False, "Attachment not found"

            # Delete physical file
            full_path = os.path.join(base_path, attachment.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError as e:
                    logger.error(f"Error deleting file {full_path}: {str(e)}")
                    return False, "Error deleting file"

            # Soft delete record
            attachment.soft_delete()
            db.session.commit()
            
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting attachment: {str(e)}")
            return False, str(e)