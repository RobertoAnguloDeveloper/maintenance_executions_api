from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
import logging

logger = logging.getLogger(__name__)

class AnswerSubmitted(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'answers_submitted'
    
    id = db.Column(db.Integer, primary_key=True)
    form_answers_id = db.Column(db.Integer, db.ForeignKey('form_answers.id'), nullable=False)
    text_answered = db.Column(db.Text)
    form_submissions_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)

    # Relationships
    form_answer = db.relationship('FormAnswer', back_populates='submissions')
    form_submission = db.relationship('FormSubmission', back_populates='answers_submitted')

    def __repr__(self):
        return f'<AnswerSubmitted {self.id}>'

    def requires_text_answer(self):
        """Check if this submission requires a text answer based on question type"""
        if self.form_answer and self.form_answer.form_question.question:
            question_type = self.form_answer.form_question.question.question_type.type
            return question_type in ['text', 'date', 'datetime']
        return False

    def to_dict(self):
        """Convert answer submitted to dictionary representation with related data."""
        try:
            # Get form answer and related data
            form_answer_data = None
            if self.form_answer:
                form_answer_data = {
                    'id': self.form_answer.id,
                    'question': {
                        'id': self.form_answer.form_question.question.id,
                        'text': self.form_answer.form_question.question.text,
                        'type': self.form_answer.form_question.question.question_type.type,
                        'remarks': self.form_answer.form_question.question.remarks
                    } if self.form_answer.form_question and self.form_answer.form_question.question else None,
                    'answer': {
                        'id': self.form_answer.answer.id,
                        'value': self.form_answer.answer.value,
                        'remarks': self.form_answer.answer.remarks
                    } if self.form_answer.answer else None
                }

            return {
                'id': self.id,
                'form_answers_id': self.form_answers_id,
                'text_answered': self.text_answered,
                'form_submissions_id': self.form_submissions_id,
                'form_answer': form_answer_data,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            logger.error(f"Error converting answer submitted to dict: {str(e)}")
            return {
                'id': self.id,
                'form_answers_id': self.form_answers_id,
                'form_submissions_id': self.form_submissions_id,
                'error': 'Error loading related data'
            }