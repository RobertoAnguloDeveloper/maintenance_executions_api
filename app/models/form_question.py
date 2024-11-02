from app import db
from app.models.timestamp_mixin import TimestampMixin

class FormQuestion(TimestampMixin, db.Model):
    __tablename__ = 'form_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    order_number = db.Column(db.Integer)

    # Relationships
    form = db.relationship('Form', back_populates='form_questions')
    question = db.relationship('Question', back_populates='form_questions')
    form_answers = db.relationship('FormAnswer', back_populates='form_question', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<FormQuestion {self.form_id}:{self.question_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'form_id': self.form_id,
            'question_id': self.question_id,
            'order_number': self.order_number,
            'question': self.question.to_dict() if self.question else None
        }