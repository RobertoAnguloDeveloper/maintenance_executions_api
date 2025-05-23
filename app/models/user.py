from app import db
from app.models.role_permission import RolePermission
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    environment_id = db.Column(db.Integer, db.ForeignKey('environments.id'))

    # Relationships
    role = db.relationship('Role', back_populates='users')
    environment = db.relationship('Environment', back_populates='users')
    created_forms = db.relationship('Form', back_populates='creator')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.updated_at = datetime.utcnow()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'contact_number': self.contact_number,
            'username': self.username,
            'role_id': self.role_id,
            'environment_id': self.environment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def to_dict(self, include_details=False, include_deleted=False):
        """
        Convert User object to dictionary representation with soft-delete awareness.
        
        Args:
            include_details (bool): Whether to include additional details
            include_deleted (bool): Whether to include soft-delete information
            
        Returns:
            dict: Dictionary representation of the user
        """
        # Get non-deleted role and environment
        active_role = self.role if self.role and not self.role.is_deleted else None
        active_environment = self.environment if self.environment and not self.environment.is_deleted else None

        base_dict = {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'contact_number': self.contact_number,
            'role': {
                "role_id": self.role_id,
                "role_name": active_role.name if active_role else None,
                "role_description": active_role.description if active_role else None
            },
            'environment': {
                "environment_id": self.environment_id,
                "environment_name": active_environment.name if active_environment else None,
                "environment_description": active_environment.description if active_environment else None
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Include soft delete information if requested
        if include_deleted:
            base_dict.update({
                'is_deleted': self.is_deleted,
                'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
            })
        
        if include_details:
            # Get active forms (not deleted)
            active_forms = [form for form in self.created_forms if not form.is_deleted] if self.created_forms else []
            
            # Get active permissions from active role
            active_permissions = []
            if active_role:
                active_permissions = [
                                        {
                                            'id': p.id,
                                            'name': p.name,
                                            'action': p.action,
                                            'entity': p.entity
                                        }
                                        for p in active_role.permissions 
                                        if not p.is_deleted  # Check permission is not deleted
                                        and not RolePermission.query.filter_by(  # Check role-permission mapping is not deleted
                                            role_id=active_role.id,
                                            permission_id=p.id,
                                            is_deleted=True
                                        ).first()
                                    ]

            details_dict = {
                'role': {
                    'id': active_role.id,
                    'name': active_role.name,
                    'description': active_role.description,
                    'is_super_user': active_role.is_super_user
                } if active_role else None,
                
                'environment': {
                    'id': active_environment.id,
                    'name': active_environment.name,
                    'description': active_environment.description
                } if active_environment else None,
                
                'created_forms_count': len(active_forms),
                'full_name': f"{self.first_name} {self.last_name}",
                'email': self.email,
                'contact_number': self.contact_number,
                'permissions': active_permissions
            }
            
            base_dict.update(details_dict)
        
        return base_dict