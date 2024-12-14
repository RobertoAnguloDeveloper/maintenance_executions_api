from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
import logging

logger = logging.getLogger(__name__)

class AnswerSubmitted(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'answers_submitted'
    
    id = db.Column(db.Integer, primary_key=True)
    form_answer_id = db.Column(db.Integer, db.ForeignKey('form_answers.id'), nullable=False)  # Changed from form_answers_id
    form_submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)  # Changed from form_submissions_id
    text_answered = db.Column(db.Text)

    # Relationships
    form_answer = db.relationship('FormAnswer', back_populates='submissions')
    form_submission = db.relationship('FormSubmission', back_populates='answers_submitted')

    def __repr__(self):
        return f'<AnswerSubmitted {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'form_answer_id': self.form_answer_id,
            'form_submission': {
                                "id": self.form_submission.id,
                                "submitted_by": self.form_submission.submitted_by,
                                "submitted_at": self.form_submission.submitted_at
                            },
            'text_answered': self.text_answered,
            'form_answer': {
                'id': self.form_answer.id,
                'question': {
                    'text': self.form_answer.form_question.question.text,
                    'type': self.form_answer.form_question.question.question_type.type
                } if self.form_answer.form_question and self.form_answer.form_question.question else None,
                'answer': {
                    'value': self.form_answer.answer.value
                } if self.form_answer.answer else None
            } if self.form_answer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }