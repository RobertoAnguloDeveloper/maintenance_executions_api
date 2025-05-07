# app/models/report_template.py

import datetime
from typing import Dict, Any
from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
# Ensure func is imported if using server defaults (inherited from TimestampMixin)
from sqlalchemy.sql import func

class ReportTemplate(TimestampMixin, SoftDeleteMixin, db.Model):
    """
    Model representing saved report configurations (templates).
    Users can save frequently used report parameters (columns, filters, etc.)
    for easy reuse.
    """
    __tablename__ = 'report_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True) # Added index
    configuration = db.Column(db.JSON, nullable=False) # Stores report params (columns, filters, type, etc.)
    is_public = db.Column(db.Boolean, default=False, nullable=False, index=True) # Added index and nullable=False

    # Relationship to the User who created the template
    # Inherits created_at, updated_at from TimestampMixin
    # Inherits is_deleted, deleted_at from SoftDeleteMixin
    user = db.relationship('User', back_populates='report_templates')

    def __repr__(self):
        """Provide a string representation for debugging."""
        return f'<ReportTemplate {self.id}: {self.name}>'

    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields, suitable for lists."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Basic view usually doesn't need delete status unless for admin lists
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def to_dict(self) -> dict:
        """Convert report template to a detailed dictionary representation."""
        user_info = None
        # Check if user relationship is loaded and not soft-deleted
        if self.user and not self.user.is_deleted:
             user_info = {
                 'id': self.user.id,
                 'username': self.user.username,
                 'full_name': f"{self.user.first_name} {self.user.last_name}"
             }

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'user': user_info, # Include basic user info
            'configuration': self.configuration, # Include the actual report parameters JSON
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Optionally include soft delete status if needed for specific views
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def find_by_id(cls, template_id: int) -> 'ReportTemplate':
        """Find a template by its ID, respecting soft delete."""
        return cls.query.filter_by(id=template_id, is_deleted=False).first()

    @classmethod
    def find_for_user(cls, user_id: int, include_public: bool = True):
        """Find templates accessible by a user (theirs + public)."""
        query = cls.query.filter(cls.is_deleted == False)
        if include_public:
            query = query.filter((cls.user_id == user_id) | (cls.is_public == True))
        else:
            query = query.filter(cls.user_id == user_id)
        return query.order_by(cls.name).all()