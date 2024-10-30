from app import db
from app.models.timestamp_mixin import TimestampMixin

class Question(TimestampMixin, db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    question_type_id = db.Column(db.Integer, db.ForeignKey('question_types.id'), nullable=False)
    order_number = db.Column(db.Integer)
    has_remarks = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    question_type = db.relationship('QuestionType', back_populates='questions')
    forms = db.relationship('Form', back_populates='question')
    
    def __repr__(self):
        return f'<Question {self.text[:20]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'question_type': self.question_type.to_dict() if self.question_type else None,
            'order_number': self.order_number,
            'has_remarks': self.has_remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }