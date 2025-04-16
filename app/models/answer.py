from typing import Optional, Tuple
from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from datetime import datetime

class Answer(TimestampMixin, SoftDeleteMixin, db.Model):
    """
    Model representing possible answers that can be associated with questions.
    This model stores the base answer options that can be used across different forms.
    """
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Text)
    remarks = db.Column(db.Text)

    # Relationships
    form_answers = db.relationship(
        'FormAnswer',
        back_populates='answer',
        cascade='all, delete-orphan'
    )

    def __init__(self, value=None, remarks=None):
        self.value = value
        self.remarks = remarks

    def __repr__(self):
        return f'<Answer {self.id}: {self.value[:20] if self.value else "No value"}>'

    def soft_delete(self):
        """Perform soft delete"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore from soft delete"""
        self.is_deleted = False
        self.deleted_at = None
        
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'value': self.value,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def to_dict(self) -> dict:
        """Convert answer to dictionary representation"""
        return {
            'id': self.id,
            'value': self.value,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_active(cls):
        """Get all non-deleted answers"""
        return cls.query.filter_by(is_deleted=False)

    @classmethod
    def get_deleted(cls):
        """Get all deleted answers"""
        return cls.query.filter_by(is_deleted=True)

    @classmethod
    def get_all_with_deleted(cls):
        """Get all answers including deleted ones"""
        return cls.query

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the answer data
        
        Returns:
            tuple: (is_valid: bool, error_message: Optional[str])
        """
        if not self.value or not self.value.strip():
            return False, "Answer value cannot be empty"
        
        if len(self.value) > 1000:  # Example max length
            return False, "Answer value exceeds maximum length of 1000 characters"
            
        return True, None