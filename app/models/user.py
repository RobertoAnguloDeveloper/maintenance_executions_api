from app import db
from app.models.timestamp_mixin import TimestampMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(TimestampMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    environment_id = db.Column(db.Integer, db.ForeignKey('environments.id'))
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

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

    def to_dict(self, include_details=False, include_deleted=False):
        """Convert User object to dictionary representation"""
        base_dict = {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'role': {
                        "role_id": self.role_id,
                        "role_name": self.role.name if self.role else None,
                        "role_description": self.role.description if self.role else None
                     },
            'environment':{
                            "environment_id": self.environment_id,
                            "environment_name": self.environment.name if self.environment else None,
                            "environment_description": self.environment.description if self.environment else None
                            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Include soft delete information for admin users
        if include_deleted:
            base_dict.update({
                'is_deleted': self.is_deleted,
                'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
            })
        
        if include_details:
            base_dict.update({
                'role': {
                    'id': self.role.id,
                    'name': self.role.name,
                    'description': self.role.description,
                    'is_super_user': self.role.is_super_user
                } if self.role else None,
                
                'environment': {
                    'id': self.environment.id,
                    'name': self.environment.name,
                    'description': self.environment.description
                } if self.environment else None,
                
                'created_forms_count': len(self.created_forms) if self.created_forms else 0,
                'full_name': f"{self.first_name} {self.last_name}",
                'permissions': [p.name for p in self.role.permissions] if self.role else []
            })
        
        return base_dict