from app import db
from sqlalchemy import asc

class BaseService:
    def __init__(self, model):
        self.model = model

    def get_all_sorted(self):
        return self.model.query.order_by(asc(self.model.id)).all()

    def get_by_id(self, id):
        return self.model.query.get(id)

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

    def delete(self, id):
        instance = self.get_by_id(id)
        if instance:
            db.session.delete(instance)
            db.session.commit()
        return instance