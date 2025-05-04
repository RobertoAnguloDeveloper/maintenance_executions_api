# app/models/token_blocklist.py
from app import db
from datetime import datetime, timezone

class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Add migration-friendly index
    __table_args__ = (
        db.Index('idx_token_blocklist_jti', 'jti'),
    )

    def __repr__(self):
        return f"<TokenBlocklist(jti={self.jti})>"