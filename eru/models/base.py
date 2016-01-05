# coding: utf-8

import json
from sqlalchemy.ext.declarative import declared_attr

from eru.utils import Jsonized
from eru.models import db
from eru.clients import rds


class Base(Jsonized, db.Model):

    __abstract__ = True

    @declared_attr
    def id(cls):
        return db.Column('id', db.Integer, primary_key=True, autoincrement=True)

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id==id).first()

    @classmethod
    def get_multi(cls, ids):
        return [cls.get(i) for i in ids]

    def to_dict(self):
        keys = [c.key for c in self.__table__.columns]
        return {k: getattr(self, k) for k in keys}

    def __repr__(self):
        attrs = ', '.join('{0}={1}'.format(k, v) for k, v in self.to_dict().iteritems())
        return '{0}({1})'.format(self.__class__.__name__, attrs)


class PropsMixin(object):
    """丢redis里"""

    def get_uuid(self):
        raise NotImplementedError('Need uuid to idenify objects')

    @property
    def _property_key(self):
        return self.get_uuid() + '/property'

    def get_props(self):
        props = rds.get(self._property_key) or '{}'
        return json.loads(props)

    def set_props(self, props):
        rds.set(self._property_key, json.dumps(props))

    def destroy_props(self):
        rds.delete(self._property_key)

    props = property(get_props, set_props, destroy_props)

    def update_props(self, **kw):
        props = self.props
        props.update(kw)
        self.props = props

    def get_props_item(self, key, default=None):
        return self.props.get(key, default)

    def set_props_item(self, key, value):
        props = self.props
        props[key] = value
        self.props = props

    def delete_props_item(self, key):
        props = self.props
        props.pop(key, None)
        self.props = props


class PropsItem(object):

    def __init__(self, name, default=None, type=None):
        self.name = name
        self.default = default
        self.type = type

    def __get__(self, obj, obj_type):
        r = obj.get_props_item(self.name, self.default)
        if self.type:
            r = self.type(r)
        return r

    def __set__(self, obj, value):
        obj.set_props_item(self.name, value)

    def __delete__(self, obj):
        obj.delete_props_item(self.name)
