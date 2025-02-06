import mimetypes
from typing import BinaryIO, Dict, Optional, Tuple, List, Union
from datetime import datetime
import os
import shutil
import logging
from werkzeug.utils import secure_filename
from app import db
from app.models.attachment import Attachment
from app.models.form import Form
from app.models.form_submission import FormSubmission
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

class AttachmentService:
    @staticmethod
    def get_unique_filename(original_filename: str) -> str:
        """Generate unique filename with timestamp"""
        # Get filename and extension
        base_name, extension = os.path.splitext(original_filename)
        # Add timestamp to filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_{timestamp}{extension}"

    @staticmethod
    def create_file_path(username: str, filename: str) -> str:
        """Create organized file path structure by user"""
        # Create single folder per user
        return os.path.join(username, filename)

    @staticmethod
    def validate_file(
        file: BinaryIO,
        filename: str,
        max_size: int = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Enhanced file validation with fallback mechanisms
        """
        try:
            if not filename:
                return False, "No filename provided"

            # Get file extension
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if not ext or ext not in Attachment.ALLOWED_EXTENSIONS:
                return False, (
                    f"File type not allowed. Allowed types: "
                    f"{', '.join(sorted(Attachment.ALLOWED_EXTENSIONS))}"
                )

            # Check file size
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            
            max_size = max_size or Attachment.MAX_FILE_SIZE
            if size > max_size:
                return False, f"File size exceeds limit of {max_size / (1024*1024)}MB"

            # Use mimetypes library as primary method for type detection
            mime_type, _ = mimetypes.guess_type(filename)
            
            # Fallback to basic extension mapping if mime type detection fails
            if not mime_type:
                mime_type = Attachment.ALLOWED_EXTENSIONS.get(ext)
            
            if not mime_type:
                return False, "Could not determine file type"

            # Special handling for text files
            if mime_type == 'text/plain' and ext == 'txt':
                return True, mime_type

            if mime_type not in Attachment.ALLOWED_MIME_TYPES.values():
                return False, (
                    f"Invalid file type (MIME: {mime_type}). "
                    f"Allowed types: {', '.join(sorted(Attachment.ALLOWED_EXTENSIONS))}"
                )

            return True, mime_type

        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, f"Error validating file: {str(e)}"
        
    @staticmethod
    def verify_file_integrity(file_path: str, base_path: str) -> bool:
        """
        Verify if file exists and is accessible
        
        Args:
            file_path: Relative path to file
            base_path: Base upload directory
            
        Returns:
            bool: True if file exists and is accessible
        """
        try:
            full_path = os.path.join(base_path, file_path)
            return os.path.isfile(full_path) and os.access(full_path, os.R_OK)
        except Exception:
            return False
        
    @staticmethod
    def cleanup_orphaned_files(base_path: str) -> Dict[str, int]:
        """
        Clean up files that don't have corresponding database records
        
        Args:
            base_path: Base upload directory path
            
        Returns:
            Dict[str, int]: Statistics about cleanup operation
        """
        stats = {'scanned': 0, 'deleted': 0, 'errors': 0}
        
        try:
            # Get all file paths from database
            db_files = set(a.file_path for a in Attachment.query.all())
            
            # Scan upload directory
            for root, _, files in os.walk(base_path):
                for file in files:
                    stats['scanned'] += 1
                    rel_path = os.path.relpath(os.path.join(root, file), base_path)
                    
                    if rel_path not in db_files:
                        try:
                            os.remove(os.path.join(root, file))
                            stats['deleted'] += 1
                        except OSError:
                            stats['errors'] += 1
                            
            return stats
        except Exception as e:
            logger.error(f"Error during orphaned files cleanup: {str(e)}")
            return stats

    @staticmethod
    def save_file(
        file: BinaryIO,
        base_path: str,
        file_path: str
    ) -> Tuple[bool, Optional[str]]:
        """Save file with proper error handling"""
        try:
            full_path = os.path.join(base_path, file_path)
            # Create user directory if it doesn't exist
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
        file_type: str = None,
        is_signature: bool = False
    ) -> Tuple[Optional[Attachment], Optional[str]]:
        """Create new attachment with enhanced validation"""
        try:
            # Validate file if file_type not provided
            if not file_type:
                is_valid, mime_type = AttachmentService.validate_file(file, filename)
                if not is_valid:
                    return None, mime_type
                file_type = mime_type

            # Secure and uniquify filename
            secure_name = secure_filename(filename)
            unique_name = AttachmentService.get_unique_filename(secure_name)
            
            # Create path with just username folder
            file_path = AttachmentService.create_file_path(username, unique_name)

            # Save file
            success, error = AttachmentService.save_file(file, upload_path, file_path)
            if not success:
                return None, error

            # Create database record
            attachment = Attachment(
                form_submission_id=form_submission_id,
                file_type=file_type,
                file_path=file_path,
                is_signature=is_signature
            )
            
            db.session.add(attachment)
            db.session.commit()
            
            logger.info(f"File saved successfully: {file_path}")
            return attachment, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating attachment: {str(e)}")
            return None, str(e)

    @staticmethod
    def bulk_create_attachments(
        form_submission_id: int,
        files: List[Dict],
        username: str,
        upload_path: str
    ) -> Tuple[Optional[List[Attachment]], Optional[str]]:
        """
        Enhanced bulk attachment creation with improved validation
        """
        try:
            created_attachments = []
            
            # Start transaction
            db.session.begin_nested()
            
            for file_data in files:
                file = file_data.get('file')
                is_signature = file_data.get('is_signature', False)
                
                if not file:
                    db.session.rollback()
                    return None, "File object is required for each attachment"
                    
                # Initial validation
                is_valid, mime_type_or_error = AttachmentService.validate_file(
                    file,
                    file.filename,
                    max_size=Attachment.MAX_FILE_SIZE
                )
                
                if not is_valid:
                    db.session.rollback()
                    return None, f"Invalid file {file.filename}: {mime_type_or_error}"

                # Generate unique filename and path
                secure_name = secure_filename(file.filename)
                unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_name}"
                file_path = os.path.join(username, unique_name)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.join(upload_path, username), exist_ok=True)
                
                # Save file
                try:
                    file.save(os.path.join(upload_path, file_path))
                except Exception as e:
                    db.session.rollback()
                    return None, f"Error saving file {file.filename}: {str(e)}"
                
                # Create attachment record
                attachment = Attachment(
                    form_submission_id=form_submission_id,
                    file_type=mime_type_or_error,
                    file_path=file_path,
                    is_signature=is_signature
                )
                
                db.session.add(attachment)
                created_attachments.append(attachment)
            
            db.session.commit()
            logger.info(f"Successfully created {len(created_attachments)} attachments")
            return created_attachments, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk_create_attachments: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_all_attachments(filters: Dict = None) -> List[Attachment]:
        """
        Get all attachments with optional filtering
        
        Args:
            filters: Optional dictionary containing filters
                - form_submission_id: Filter by form submission
                - is_signature: Filter by signature type
                - file_type: Filter by file type
                
        Returns:
            List[Attachment]: List of attachment objects
        """
        try:
            query = Attachment.query.filter_by(is_deleted=False)
            
            if filters:
                if 'form_submission_id' in filters:
                    query = query.filter_by(form_submission_id=filters['form_submission_id'])
                    
                if 'is_signature' in filters:
                    query = query.filter_by(is_signature=filters['is_signature'])
                    
                if 'file_type' in filters:
                    query = query.filter_by(file_type=filters['file_type'])
            
            # Join with form_submission to get additional details
            query = (query.join(FormSubmission)
                    .options(joinedload(Attachment.form_submission)))
                    
            return query.order_by(Attachment.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error getting attachments: {str(e)}")
            raise
        
    @staticmethod
    def get_attachment(attachment_id: int) -> Optional[Attachment]:
        """
        Get non-deleted attachment by ID with relationships
        
        Args:
            attachment_id: ID of the attachment to retrieve
            
        Returns:
            Optional[Attachment]: Attachment object if found and not deleted
        """
        try:
            return Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).options(
                joinedload(Attachment.form_submission)
                .joinedload(FormSubmission.form)
                .joinedload(Form.creator)
            ).first()
        except Exception as e:
            logger.error(f"Error getting attachment {attachment_id}: {str(e)}")
            return None
        
    @staticmethod
    def get_attachment_with_file(
        attachment_id: int,
        base_path: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get attachment with file data with enhanced logging
        """
        try:
            # Get attachment record
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).first()
                
            if not attachment:
                logger.error(f"Attachment {attachment_id} not found in database")
                return None, "Attachment not found"

            # Log attachment details
            logger.info(f"Found attachment record: {attachment.id}")
            logger.info(f"Stored file path: {attachment.file_path}")
            logger.info(f"Base path: {base_path}")
            
            # Construct full file path
            full_path = os.path.normpath(os.path.join(base_path, attachment.file_path))
            logger.info(f"Attempting to access file at: {full_path}")
                
            # Log directory contents
            dir_path = os.path.dirname(full_path)
            if os.path.exists(dir_path):
                logger.info(f"Directory contents of {dir_path}:")
                for file in os.listdir(dir_path):
                    logger.info(f" - {file}")
            else:
                logger.error(f"Directory does not exist: {dir_path}")
                
            # Check if file exists
            if not os.path.exists(full_path):
                logger.error(f"File not found at path: {full_path}")
                return None, "File not found"
                    
            logger.info(f"Successfully found file at: {full_path}")
            return {
                'record': attachment,
                'file_path': full_path,
                'filename': os.path.basename(attachment.file_path)
            }, None
                
        except Exception as e:
            logger.error(f"Error getting attachment: {str(e)}", exc_info=True)
            return None, str(e)
        
    @staticmethod
    def physically_delete_file(file_path: str, base_path: str) -> Tuple[bool, Optional[str]]:
        """
        Physically delete file and cleanup empty directories
        
        Args:
            file_path: Relative path to file from base_path
            base_path: Base upload directory path
            
        Returns:
            tuple: (Success boolean, Error message if any)
        """
        try:
            full_path = os.path.join(base_path, file_path)
            
            # Security check - ensure file path is within base path
            if not os.path.commonpath([base_path, full_path]) == base_path:
                return False, "Invalid file path - possible path traversal attempt"
            
            # Check if file exists
            if not os.path.exists(full_path):
                logger.warning(f"File not found for deletion: {full_path}")
                return True, None  # Consider it success if file doesn't exist
                
            # Delete the file
            os.remove(full_path)
            logger.info(f"File deleted successfully: {full_path}")
            
            # Get directory path
            dir_path = os.path.dirname(full_path)
            
            # Clean up empty directories
            while dir_path != base_path:
                if len(os.listdir(dir_path)) == 0:
                    os.rmdir(dir_path)
                    logger.info(f"Removed empty directory: {dir_path}")
                    dir_path = os.path.dirname(dir_path)
                else:
                    break
                    
            return True, None
            
        except PermissionError as e:
            error_msg = f"Permission denied when deleting file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except OSError as e:
            error_msg = f"OS error when deleting file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error deleting file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        
    @staticmethod
    def delete_attachment(
        attachment_id: int,
        base_path: str
    ) -> Tuple[bool, Union[Dict, str]]:
        """
        Delete attachment with physical file removal and soft delete record
        
        Args:
            attachment_id: ID of the attachment to delete
            base_path: Base upload directory path
            
        Returns:
            tuple: (Success boolean, Result dictionary or error message)
        """
        try:
            # Get attachment checking is_deleted=False
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).first()
            
            if not attachment:
                return False, "Attachment not found"

            # Delete physical file first
            success, error = AttachmentService.physically_delete_file(
                file_path=attachment.file_path,
                base_path=base_path
            )
            
            if not success:
                return False, f"Error deleting file: {error}"

            # Perform soft delete
            deletion_stats = {
                'attachment_id': attachment.id,
                'file_path': attachment.file_path,
                'deleted_at': datetime.utcnow().isoformat()
            }
            
            attachment.soft_delete()
            db.session.commit()
            
            logger.info(f"Attachment {attachment_id} deleted successfully")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting attachment: {str(e)}"
            logger.error(error_msg)
            return False, error_msg