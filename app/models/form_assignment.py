# app/models/form_assignment.py

from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin

class FormAssignment(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'form_assignments'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    entity_name = db.Column(db.String(50), nullable=False) # e.g., 'user', 'role', 'environment'
    entity_id = db.Column(db.Integer, nullable=False) # ID of the user, role, or environment

    # Relationships
    form = db.relationship('Form', back_populates='form_assignments')

    # Add a unique constraint for form_id, entity_name, and entity_id
    __table_args__ = (db.UniqueConstraint('form_id', 'entity_name', 'entity_id', name='_form_entity_uc'),)

    def __repr__(self):
        return f'<FormAssignment form_id={self.form_id} entity={self.entity_name}:{self.entity_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'form_id': self.form_id,
            'entity_name': self.entity_name,
            'entity_id': self.entity_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def to_dict_basic(self):
        return self.to_dict()