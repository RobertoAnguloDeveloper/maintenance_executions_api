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

    role = db.relationship('Role', back_populates='users')
    environment = db.relationship('Environment', back_populates='users')
    created_forms = db.relationship('Form', back_populates='creator', foreign_keys='Form.user_id')  # Cambiado de creator_id a user_id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.updated_at = datetime.utcnow()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self, include_details=False):
        """
        Convert User object to dictionary representation
        
        Args:
            include_details (bool): Whether to include detailed information like role and environment
            
        Returns:
            dict: Dictionary representation of the User
        """
        base_dict = {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'role_id': self.role_id,
            'environment_id': self.environment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_details:
            # Include role information
            base_dict['role'] = {
                'id': self.role.id,
                'name': self.role.name,
                'description': self.role.description,
                'is_super_user': self.role.is_super_user
            } if self.role else None
            
            # Include environment information
            base_dict['environment'] = {
                'id': self.environment.id,
                'name': self.environment.name,
                'description': self.environment.description
            } if self.environment else None
            
            # Include forms count
            base_dict['created_forms_count'] = len(self.created_forms) if self.created_forms else 0
            
            # Additional user details
            base_dict['full_name'] = f"{self.first_name} {self.last_name}"
            base_dict['permissions'] = [p.name for p in self.role.permissions] if self.role else []
        
        return base_dict