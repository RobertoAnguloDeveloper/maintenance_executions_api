from app import db
from sqlalchemy.sql import func
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin

class Permission(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    action = db.Column(db.String(10), nullable=False)
    entity = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    role_permissions = db.relationship('RolePermission', back_populates='permission', overlaps="roles")
    roles = db.relationship('Role', secondary='role_permissions', back_populates='permissions', overlaps="role_permissions,role")

    def __repr__(self):
        return f'<Permission {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'entity': self.entity,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()