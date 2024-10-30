from app import db
from app.models.timestamp_mixin import TimestampMixin

class Form(TimestampMixin, db.Model):
    __tablename__ = 'forms'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)
    is_public = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    creator = db.relationship('User', back_populates='created_forms')
    question = db.relationship('Question', back_populates='forms')
    answer = db.relationship('Answer', back_populates='forms')
    form_submissions = db.relationship('FormSubmission', back_populates='form')
    
    def __repr__(self):
        return f'<Form {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id,
            'question_id': self.question_id,
            'answer_id': self.answer_id,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'question': self.question.to_dict() if self.question else None,
            'answer': self.answer.to_dict() if self.answer else None
        }