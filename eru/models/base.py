# coding: utf-8

from sqlalchemy.ext.declarative import declared_attr

from eru.models import db


class Base(db.Model):

    __abstract__ = True

    @declared_attr
    def id(cls):
        return db.Column('id', db.Integer, primary_key=True, autoincrement=True)

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id==id).first()

    def to_dict(self):
        keys = [c.key for c in self.__table__.columns]
        return {k: getattr(self, k) for k in keys}

