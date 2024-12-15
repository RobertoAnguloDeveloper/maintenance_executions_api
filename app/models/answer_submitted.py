from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
import logging

logger = logging.getLogger(__name__)

class AnswerSubmitted(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'answers_submitted'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text)
    question_type = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text)
    form_submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)

    # Relationships
    form_submission = db.relationship('FormSubmission', back_populates='answers_submitted')

    def __repr__(self):
        return f'<AnswerSubmitted {self.id}>'

    def to_dict(self):
        """Convert answer submission to dictionary representation"""
        return {
            'id': self.id,
            'question': self.question,
            'question_type': self.question_type,
            'answer': self.answer,
            'form_submission': {
                "id": self.form_submission.id,
                "submitted_by": self.form_submission.submitted_by,
                "submitted_at": self.form_submission.submitted_at.isoformat() if self.form_submission.submitted_at else None,
                "form": {
                    "id": self.form_submission.form.id,
                    "title": self.form_submission.form.title
                } if self.form_submission.form else None
            } if self.form_submission else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }