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

    @classmethod
    def get_multi(cls, ids):
        #return cls.query.filter(cls.id._in(tuple(ids))).all()
        return [cls.get(i) for i in ids]

    def to_dict(self):
        keys = [c.key for c in self.__table__.columns]
        return {k: getattr(self, k) for k in keys}

    def __repr__(self):
        attrs = ', '.join('{0}={1}'.format(k, v) for k, v in self.to_dict().iteritems())
        return '{0}({1})'.format(self.__class__.__name__, attrs)

