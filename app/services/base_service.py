from app import db
from sqlalchemy import asc

class BaseService:
    def __init__(self, model):
        self.model = model

    def get_all_sorted(self, include_deleted=False):
        query = self.model.query if include_deleted else self.model.get_active()
        return query.order_by(asc(self.model.id)).all()

    def get_by_id(self, id, include_deleted=False):
        query = self.model.query if include_deleted else self.model.get_active()
        return query.get(id)

    def create(self, **kwargs):
        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    def update(self, id, **kwargs):
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            db.session.commit()
        return instance

    def delete(self, id, soft=True):
        instance = self.get_by_id(id)
        if instance:
            if soft:
                instance.soft_delete()
                db.session.commit()
            else:
                db.session.delete(instance)
                db.session.commit()
        return instance

    def restore(self, id):
        instance = self.get_by_id(id, include_deleted=True)
        if instance:
            instance.restore()
            db.session.commit()
        return instance