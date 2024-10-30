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