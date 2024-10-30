from app import db
from app.models.timestamp_mixin import TimestampMixin

class FormSubmission(TimestampMixin, db.Model):
    __tablename__ = 'form_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    submitted_at = db.Column(db.DateTime)
    username = db.Column(db.String(50), unique=True, nullable=False)

    # Relationships
    form = db.relationship('Form', back_populates='form_submissions')
    attachments = db.relationship('Attachment', back_populates='form_submission', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FormSubmission {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'form_id': self.form_id,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'attachments': [attachment.to_dict() for attachment in self.attachments]
        }