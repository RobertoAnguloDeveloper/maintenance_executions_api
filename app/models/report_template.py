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
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False, index=True) # Changed from user_id to form_id
    configuration = db.Column(db.JSON, nullable=False) # Stores report params (columns, filters, type, etc.)
    is_public = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Relationship to the Form for which this template is created
    # Inherits created_at, updated_at from TimestampMixin
    # Inherits is_deleted, deleted_at from SoftDeleteMixin
    form = db.relationship('Form', back_populates='report_templates') # Changed from 'User' to 'Form'

    def __repr__(self):
        """Provide a string representation for debugging."""
        return f'<ReportTemplate {self.id}: {self.name}>'

    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields, suitable for lists."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'form_id': self.form_id, # Changed from user_id to form_id
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Basic view usually doesn't need delete status unless for admin lists
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def to_dict(self) -> dict:
        """Convert report template to a detailed dictionary representation."""
        form_info = None
        # Check if form relationship is loaded and not soft-deleted
        if self.form and not self.form.is_deleted:
             form_info = {
                 'id': self.form.id,
                 'title': self.form.title,
                 'description': self.form.description
             }
             
             # If the form's creator relationship is loaded, include creator info
             if hasattr(self.form, 'creator') and self.form.creator:
                 form_info['created_by'] = {
                     'id': self.form.creator.id,
                     'username': self.form.creator.username,
                     'full_name': f"{self.form.creator.first_name} {self.form.creator.last_name}"
                 }

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'form_id': self.form_id, # Changed from user_id to form_id
            'form': form_info, # Include basic form info, changed from user_info
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
        """
        Find templates accessible by a user (templates for their forms + public templates).
        
        Args:
            user_id (int): The ID of the user.
            include_public (bool): Whether to include public templates.
            
        Returns:
            List of ReportTemplate objects that the user can access.
        """
        from app.models.form import Form
        
        # Get forms created by the user
        user_form_ids = db.session.query(Form.id).filter(
            Form.user_id == user_id, 
            Form.is_deleted == False
        ).all()
        user_form_ids = [f[0] for f in user_form_ids]
        
        # Build the query for report templates
        query = cls.query.filter(cls.is_deleted == False)
        
        if include_public:
            # User can access templates for their forms OR public templates
            query = query.filter((cls.form_id.in_(user_form_ids)) | (cls.is_public == True))
        else:
            # User can access only templates for their forms
            query = query.filter(cls.form_id.in_(user_form_ids))
            
        return query.order_by(cls.name).all()