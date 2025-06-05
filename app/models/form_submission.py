# app/models/form_submission.py
from typing import Any, Dict, List
from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from datetime import datetime

class FormSubmission(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'form_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    submitted_by = db.Column(db.String(50), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    form = db.relationship('Form', back_populates='submissions')
    answers_submitted = db.relationship(
        'AnswerSubmitted',
        back_populates='form_submission',
        cascade='all, delete-orphan'
    )
    attachments = db.relationship(
        'Attachment',
        back_populates='form_submission',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<FormSubmission {self.id} by {self.submitted_by}>'
    
    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp to ISO format."""
        return timestamp.isoformat() if timestamp else None

    def to_compact_dict(self) -> Dict[str, Any]:
        """Return a compact dictionary representation for the /compact-list endpoint."""
        answers_count = 0
        if self.answers_submitted: # Check if the list is not None
            answers_count = sum(1 for ans in self.answers_submitted if not ans.is_deleted)
        
        signatures_count = 0
        non_signature_attachments_count = 0
        if self.attachments: # Check if the list is not None
            for att in self.attachments:
                if not att.is_deleted:
                    if att.is_signature:
                        signatures_count += 1
                    else:
                        non_signature_attachments_count += 1
        
        return {
            'id': self.id,
            'form_id': self.form_id,
            'form_title': self.form.title if self.form else None, # Get title from related form
            'submitted_at': self._format_timestamp(self.submitted_at),
            'submitted_by': self.submitted_by,
            'answers_count': answers_count,
            'signatures_count': signatures_count,
            'attachments_count': non_signature_attachments_count, # Adjusted count
        }

    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'form_id': self.form_id,
            'submitted_by': self.submitted_by,
            'submitted_at': self._format_timestamp(self.submitted_at),
            'created_at': self._format_timestamp(self.created_at),
            'updated_at': self._format_timestamp(self.updated_at),
            'is_deleted': self.is_deleted,
            'deleted_at': self._format_timestamp(self.deleted_at)
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert form submission to dictionary representation"""
        return {
            'id': self.id,
            'form_id': self.form_id,
            'form': {
                'id': self.form.id,
                'title': self.form.title,
                'description': self.form.description
            } if self.form else None,
            'submitted_by': self.submitted_by,
            'submitted_at': self._format_timestamp(self.submitted_at),
            'answers': [answer.to_dict() for answer in self.answers_submitted if not answer.is_deleted] if self.answers_submitted else [],
            'attachments': [attachment.to_dict() for attachment in self.attachments if not attachment.is_deleted] if self.attachments else [],
            'created_at': self._format_timestamp(self.created_at),
            'updated_at': self._format_timestamp(self.updated_at)
        }

    def get_answers(self) -> List[Dict[str, Any]]:
        """Get all answers for this submission"""
        return [answer.to_dict() for answer in self.answers_submitted if not answer.is_deleted] if self.answers_submitted else []