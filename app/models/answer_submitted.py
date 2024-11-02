from app import db
from app.models.timestamp_mixin import TimestampMixin

class AnswerSubmitted(TimestampMixin, db.Model):
    __tablename__ = 'answers_submitted'
    
    id = db.Column(db.Integer, primary_key=True)
    form_answer_id = db.Column(db.Integer, db.ForeignKey('form_answers.id'), nullable=False)
    form_submission_id = db.Column(db.Integer, db.ForeignKey('form_submissions.id'), nullable=False)

    # Relationships
    form_answer = db.relationship('FormAnswer', back_populates='submissions')
    form_submission = db.relationship('FormSubmission', back_populates='answers_submitted')

    def __repr__(self):
        return f'<AnswerSubmitted {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'form_answer_id': self.form_answer_id,
            'form_submission_id': self.form_submission_id,
            'answer': self.form_answer.to_dict() if self.form_answer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }