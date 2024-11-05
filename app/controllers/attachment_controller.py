from app.services.attachment_service import AttachmentService
import logging

logger = logging.getLogger(__name__)

class AttachmentController:
    @staticmethod
    def create_attachment(form_submission_id, file_type, file_path, file_name, file_size, is_signature=False):
        """
        Create a new attachment
        """
        return AttachmentService.create_attachment(
            form_submission_id=form_submission_id,
            file_type=file_type,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            is_signature=is_signature
        )

    @staticmethod
    def get_attachment(attachment_id):
        """Get a specific attachment"""
        return AttachmentService.get_attachment(attachment_id)

    @staticmethod
    def get_attachments_by_submission(form_submission_id):
        """Get all attachments for a form submission"""
        return AttachmentService.get_attachments_by_submission(form_submission_id)

    @staticmethod
    def get_signature_attachment(form_submission_id):
        """Get signature attachment for a form submission"""
        return AttachmentService.get_signature_attachment(form_submission_id)

    @staticmethod
    def update_attachment(attachment_id, **kwargs):
        """Update an attachment's details"""
        return AttachmentService.update_attachment(attachment_id, **kwargs)

    @staticmethod
    def delete_attachment(attachment_id):
        """Delete an attachment"""
        return AttachmentService.delete_attachment(attachment_id)

    @staticmethod
    def get_attachments_stats(form_submission_id=None):
        """Get attachment statistics"""
        return AttachmentService.get_attachments_stats(form_submission_id)