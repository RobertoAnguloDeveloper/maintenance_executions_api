from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin

class QuestionType(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'question_types'
    TYPE_DATETIME = 'datetime'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(255), nullable=False)
    
    # Relationships
    questions = db.relationship('Question', back_populates='question_type', lazy='dynamic')
    
    @classmethod
    def initialize_types(cls):
        default_types = [
            'text', 'multiple_choices', 
            'single_choice', 'date', 'datetime','user'
        ]
    
    def __repr__(self):
        return f'<QuestionType {self.type}>'
    
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }