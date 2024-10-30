from app.services.attachment_service import AttachmentService

class AttachmentController:
    @staticmethod
    def create_attachment(form_submission_id, file_type, file_path, file_name, file_size, is_signature=False):
        return AttachmentService.create_attachment(form_submission_id, file_type, file_path, file_name, file_size, is_signature)

    @staticmethod
    def get_attachment(attachment_id):
        return AttachmentService.get_attachment(attachment_id)

    @staticmethod
    def get_attachments_by_submission(form_submission_id):
        return AttachmentService.get_attachments_by_submission(form_submission_id)

    @staticmethod
    def update_attachment(attachment_id, **kwargs):
        return AttachmentService.update_attachment(attachment_id, **kwargs)

    @staticmethod
    def delete_attachment(attachment_id):
        return AttachmentService.delete_attachment(attachment_id)