from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin

class Attachment(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    form_submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    is_signature = db.Column(db.Boolean, nullable=False)

    # Relationship
    form_submission = db.relationship(
        'FormSubmission',
        back_populates='attachments'
    )
    
    def __repr__(self):
        return f'<Attachment {self.file_path}>'
    
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