from app import db
from sqlalchemy.sql import func
from datetime import datetime

class SoftDeleteMixin:
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(is_deleted=False)

    @classmethod
    def get_deleted(cls):
        return cls.query.filter_by(is_deleted=True)

    @classmethod
    def get_all_with_deleted(cls):
        return cls.query