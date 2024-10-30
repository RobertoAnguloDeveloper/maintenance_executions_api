from app import db
from sqlalchemy.sql import func
from app.models.timestamp_mixin import TimestampMixin

class RolePermission(TimestampMixin, db.Model):
    __tablename__ = 'role_permissions'
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    role = db.relationship('Role', back_populates='role_permissions', overlaps="permissions,roles")
    permission = db.relationship('Permission', back_populates='role_permissions', overlaps="permissions,roles")

    __table_args__ = (db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)

    def __repr__(self):
        return f'<RolePermission role_id={self.role_id} permission_id={self.permission_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'role_id': self.role_id,
            'permission_id': self.permission_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }