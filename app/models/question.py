from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin

class Question(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    question_type_id = db.Column(db.Integer, db.ForeignKey('question_types.id'), nullable=False)
    has_remarks = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    question_type = db.relationship('QuestionType', back_populates='questions')
    form_questions = db.relationship('FormQuestion', back_populates='question', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Question {self.text[:20]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'question_type_id': self.question_type_id,
            'question_type': self.question_type.to_dict() if self.question_type else None,
            'has_remarks': self.has_remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }