from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin

class FormAnswer(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'form_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    form_question_id = db.Column(db.Integer, db.ForeignKey('form_questions.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)

    # Relationships
    form_question = db.relationship('FormQuestion', back_populates='form_answers')
    answer = db.relationship('Answer', back_populates='form_answers')
    submissions = db.relationship(
        'AnswerSubmitted',
        back_populates='form_answer',
        foreign_keys='AnswerSubmitted.form_answer_id'
    )

    def get_question_type(self):
        """Get the question type for this form answer"""
        if self.form_question and self.form_question.question:
            return self.form_question.question.question_type.type
        return None

    def requires_text_answer(self):
        """Check if this form answer requires text input"""
        question_type = self.get_question_type()
        return question_type in ['text', 'date', 'datetime']

    def to_dict(self):
        return {
            'id': self.id,
            'form_question': {
                "id": self.form_question_id,
                "form": self.form_question.form.title if self.form_question and self.form_question.form else None,
                "question": {
                    "text": self.form_question.question.text,
                    "type": self.get_question_type()
                } if self.form_question and self.form_question.question else None
            },
            'answer': self.answer.to_dict() if self.answer else None,
            'requires_text_answer': self.requires_text_answer()
        }