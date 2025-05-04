# app/models/token_blocklist.py
from app import db
from datetime import datetime, timezone

class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist' # Optional: Define table name explicitly

    id = db.Column(db.Integer, primary_key=True)
    # JWT ID: A unique identifier for the token
    jti = db.Column(db.String(36), nullable=False, index=True, unique=True)
    # Store when the token was added to the blocklist
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<TokenBlocklist(jti={self.jti})>"