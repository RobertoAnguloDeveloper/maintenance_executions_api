# app/controllers/attachment_controller.py

from app.services.attachment_service import AttachmentService
from werkzeug.utils import secure_filename
import logging
import os

logger = logging.getLogger(__name__)

class AttachmentController:
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple:
        """
        Validate file before processing
        
        Args:
            filename (str): Name of the file
            file_size (int): Size of the file in bytes
            
        Returns:
            tuple: (bool success, str error_message)
        """
        try:
            if not filename:
                return False, "No filename provided"

            # Check file extension
            if '.' not in filename:
                return False, "No file extension provided"

            if filename.rsplit('.', 1)[1].lower() not in AttachmentController.ALLOWED_EXTENSIONS:
                return False, f"File type not allowed. Allowed types: {', '.join(AttachmentController.ALLOWED_EXTENSIONS)}"

            # Check file size
            if file_size > AttachmentController.MAX_FILE_SIZE:
                return False, f"File size exceeds limit of {AttachmentController.MAX_FILE_SIZE / (1024*1024)}MB"

            return True, None
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return False, str(e)

    @staticmethod
    def create_attachment(
        form_submission_id: int, 
        file_type: str, 
        file_path: str, 
        file_name: str,
        file_size: int,
        is_signature: bool = False
    ) -> tuple:
        """
        Create a new attachment with validation
        
        Args:
            form_submission_id (int): ID of the form submission
            file_type (str): MIME type of the file
            file_path (str): Path where file is stored
            file_name (str): Original name of the file
            file_size (int): Size of the file in bytes
            is_signature (bool): Whether this is a signature file
            
        Returns:
            tuple: (Attachment object, error message)
        """
        try:
            # Validate file
            is_valid, error = AttachmentController.validate_file(file_name, file_size)
            if not is_valid:
                return None, error

            return AttachmentService.create_attachment(
                form_submission_id=form_submission_id,
                file_type=file_type,
                file_path=file_path,
                file_name=file_name,
                is_signature=is_signature
            )
        except Exception as e:
            logger.error(f"Controller error creating attachment: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_attachment(attachment_id: int) -> tuple:
        """
        Get a specific attachment
        
        Args:
            attachment_id (int): ID of the attachment
            
        Returns:
            tuple: (Attachment object, error message)
        """
        try:
            attachment = AttachmentService.get_attachment(attachment_id)
            if not attachment:
                return None, "Attachment not found"
            return attachment, None
        except Exception as e:
            logger.error(f"Error getting attachment {attachment_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_attachments_by_submission(form_submission_id: int, include_deleted: bool = False) -> tuple:
        """
        Get all attachments for a submission
        
        Args:
            form_submission_id (int): ID of the form submission
            include_deleted (bool): Whether to include soft-deleted attachments
            
        Returns:
            tuple: (list of Attachment objects, error message)
        """
        try:
            attachments = AttachmentService.get_attachments_by_submission(
                form_submission_id,
                include_deleted
            )
            return attachments, None
        except Exception as e:
            logger.error(f"Error getting attachments for submission {form_submission_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_signature_attachment(form_submission_id: int) -> tuple:
        """
        Get signature attachment for a submission
        
        Args:
            form_submission_id (int): ID of the form submission
            
        Returns:
            tuple: (Attachment object, error message)
        """
        try:
            attachment = AttachmentService.get_signature_attachment(form_submission_id)
            if not attachment:
                return None, "Signature attachment not found"
            return attachment, None
        except Exception as e:
            logger.error(f"Error getting signature for submission {form_submission_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def update_attachment(attachment_id: int, **kwargs) -> tuple:
        """
        Update an attachment's details
        
        Args:
            attachment_id (int): ID of the attachment
            **kwargs: Fields to update
            
        Returns:
            tuple: (Updated Attachment object, error message)
        """
        try:
            # Validate updateable fields
            allowed_fields = {'file_type', 'is_signature'}
            update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not update_data:
                return None, "No valid fields to update"

            return AttachmentService.update_attachment(attachment_id, **update_data)
        except Exception as e:
            logger.error(f"Error updating attachment {attachment_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_attachment(attachment_id: int) -> tuple:
        """
        Delete an attachment
        
        Args:
            attachment_id (int): ID of the attachment
            
        Returns:
            tuple: (bool success, error message)
        """
        try:
            # Get attachment first to ensure it exists
            attachment = AttachmentService.get_attachment(attachment_id)
            if not attachment:
                return False, "Attachment not found"

            # Delete file from storage if it exists
            full_path = os.path.join(os.getenv('UPLOAD_FOLDER', 'uploads'), attachment.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError as e:
                    logger.error(f"Error deleting file {full_path}: {str(e)}")
                    # Continue with database deletion even if file deletion fails

            return AttachmentService.delete_attachment(attachment_id)
        except Exception as e:
            logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_attachments_stats(form_submission_id: int = None) -> tuple:
        """
        Get attachment statistics
        
        Args:
            form_submission_id (int, optional): ID of the form submission
            
        Returns:
            tuple: (dict statistics, error message)
        """
        try:
            stats = AttachmentService.get_attachments_stats(form_submission_id)
            if stats is None:
                return None, "Error generating statistics"
            return stats, None
        except Exception as e:
            logger.error(f"Error getting attachment statistics: {str(e)}")
            return None, str(e)

    @staticmethod
    def bulk_delete_attachments(attachment_ids: list) -> tuple:
        """
        Delete multiple attachments
        
        Args:
            attachment_ids (list): List of attachment IDs to delete
            
        Returns:
            tuple: (dict results, error message)
        """
        try:
            results = {
                'successful': [],
                'failed': []
            }

            for attachment_id in attachment_ids:
                success, error = AttachmentController.delete_attachment(attachment_id)
                if success:
                    results['successful'].append(attachment_id)
                else:
                    results['failed'].append({
                        'id': attachment_id,
                        'error': error
                    })

            return results, None
        except Exception as e:
            logger.error(f"Error in bulk deletion: {str(e)}")
            return None, str(e)