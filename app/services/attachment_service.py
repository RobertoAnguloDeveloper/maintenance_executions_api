from app import db
from app.models.attachment import Attachment
from sqlalchemy.exc import IntegrityError

class AttachmentService:
    @staticmethod
    def create_attachment(form_submission_id, file_type, file_path, file_name, file_size, is_signature=False):
        try:
            new_attachment = Attachment(
                form_submission_id=form_submission_id,
                file_type=file_type,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                is_signature=is_signature
            )
            db.session.add(new_attachment)
            db.session.commit()
            return new_attachment, None
        except IntegrityError:
            db.session.rollback()
            return None, "Error creating attachment. Please check the form_submission_id."
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_attachment(attachment_id):
        return Attachment.query.get(attachment_id)

    @staticmethod
    def get_attachments_by_submission(form_submission_id):
        return Attachment.get_attachments_by_submission(form_submission_id)

    @staticmethod
    def update_attachment(attachment_id, **kwargs):
        attachment = Attachment.query.get(attachment_id)
        if attachment:
            for key, value in kwargs.items():
                if hasattr(attachment, key):
                    setattr(attachment, key, value)
            try:
                db.session.commit()
                return attachment, None
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Attachment not found"

    @staticmethod
    def delete_attachment(attachment_id):
        attachment = Attachment.query.get(attachment_id)
        if attachment:
            try:
                db.session.delete(attachment)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Attachment not found"