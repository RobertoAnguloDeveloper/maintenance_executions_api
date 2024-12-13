from typing import Optional, Tuple
from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
import os
from werkzeug.utils import secure_filename
import mimetypes
import logging

logger = logging.getLogger(__name__)

class Attachment(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    form_submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    is_signature = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    form_submission = db.relationship('FormSubmission', back_populates='attachments')
    
    # Constants for file validation
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    ALLOWED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/gif': 'gif',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx'
    }

    def __repr__(self):
        return f'<Attachment {self.id}: {self.file_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'form_submission_id': self.form_submission_id,
            'file_type': self.file_type,
            'file_path': self.file_path,
            'is_signature': self.is_signature,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def is_allowed_file(cls, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def is_allowed_mime_type(cls, file_content: bytes) -> Tuple[bool, str]:
        """Check if file's MIME type is allowed"""
        import magic
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type in cls.ALLOWED_MIME_TYPES:
            return True, mime_type
        return False, ""

    @classmethod
    def get_mime_type(cls, filename: str) -> tuple[bool, str]:
        """Get MIME type from filename"""
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type in cls.ALLOWED_MIME_TYPES:
            return True, mime_type
        return False, ""

    @classmethod
    def validate_file(cls, file, filename: str) -> tuple[bool, Optional[str]]:
        """Validate file type and size"""
        if not filename:
            return False, "No filename provided"

        if not cls.is_allowed_file(filename):
            return False, f"File type not allowed. Allowed types: {', '.join(cls.ALLOWED_EXTENSIONS)}"

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)

        if size > cls.MAX_FILE_SIZE:
            return False, f"File size exceeds limit of {cls.MAX_FILE_SIZE / (1024*1024)}MB"

        is_valid_mime, _ = cls.get_mime_type(filename)
        if not is_valid_mime:
            return False, "Invalid file type"

        return True, None