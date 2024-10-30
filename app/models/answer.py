from app import db
from app.models.timestamp_mixin import TimestampMixin

class Answer(TimestampMixin, db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Text)
    remarks = db.Column(db.Text)

    # Relationships
    forms = db.relationship('Form', back_populates='answer')
    
    def __repr__(self):
        return f'<Answer {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'value': self.value,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }