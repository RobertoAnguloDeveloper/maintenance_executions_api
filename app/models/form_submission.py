from app import db
from app.models.timestamp_mixin import TimestampMixin
from datetime import datetime

class FormSubmission(TimestampMixin, db.Model):
    __tablename__ = 'form_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    submitted_by = db.Column(db.String(50), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    form = db.relationship('Form', back_populates='submissions')
    answers_submitted = db.relationship('AnswerSubmitted', back_populates='form_submission', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', back_populates='form_submission', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<FormSubmission {self.id} by {self.submitted_by}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'form_id': self.form_id,
            'submitted_by': self.submitted_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'answers': [answer.to_dict() for answer in self.answers_submitted],
            'attachments': [attachment.to_dict() for attachment in self.attachments]
        }