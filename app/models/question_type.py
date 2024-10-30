from app import db
from app.models.timestamp_mixin import TimestampMixin

class QuestionType(TimestampMixin, db.Model):
    __tablename__ = 'question_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(255), nullable=False)
    
    # Relationships
    questions = db.relationship('Question', back_populates='question_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<QuestionType {self.type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }