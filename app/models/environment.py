# app/models/environment.py

from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from datetime import datetime

class Environment(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'environments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)

    # Relationships
    users = db.relationship('User', back_populates='environment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f'<Environment {self.name}>'
    
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    def to_dict(self, include_details=False, include_deleted=False):
        """
        Convert Environment object to dictionary representation with soft-delete awareness.
        
        Args:
            include_details (bool): Whether to include additional details like related data
            include_deleted (bool): Whether to include soft-delete information
            
        Returns:
            dict: Dictionary representation of the environment
        """
        # Base dictionary with core information
        base_dict = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        # Include soft delete information if requested
        if include_deleted:
            base_dict.update({
                'is_deleted': self.is_deleted,
                'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
            })

        # Include additional details if requested
        if include_details:
            # Get active users (not deleted)
            active_users = [user for user in self.users if not user.is_deleted] if self.users else []
            
            details_dict = {
                'users_count': len(active_users),
                'users': [{
                    'id': user.id,
                    'username': user.username,
                    'full_name': f"{user.first_name} {user.last_name}"
                } for user in active_users] if include_details else []
            }
            
            base_dict.update(details_dict)

        return base_dict