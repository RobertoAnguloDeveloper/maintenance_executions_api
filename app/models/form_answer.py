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
    submissions = db.relationship('AnswerSubmitted', back_populates='form_answer')

    def __repr__(self):
        return f'<FormAnswer {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'form_question': {
                                "id":self.form_question_id,
                                "form": self.form_question.form.title,
                                "question": self.form_question.question.text
                                },
            'answer': self.answer.to_dict() if self.answer else None
        }