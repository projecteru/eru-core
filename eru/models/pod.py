#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base


class Pod(Base):
    __tablename__ = 'pod'

    name = db.Column(db.CHAR(30), nullable=False, unique=True)
    description = db.Column(db.Text)

    hosts = db.relationship('Host', backref='pod', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description

    @classmethod
    def create(cls, name, description=''):
        try:
            pod = cls(name, description)
            db.session.add(pod)
            db.session.commit()
            return pod
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).one()

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id==id).one()

    def assigned_to_group(self, group):
        """这个 pod 就归这个 group 啦."""
        if not group:
            return False
        group.pods.append(self)
        db.session.add(group)
        db.session.commit()
        return True

    def get_free_public_hosts(self, limit):
        """没有被标记给 group 的 hosts"""
        from .host import Host
        return self.hosts.filter(Host.group_id == None)\
                .order_by(Host.count).limit(limit).all()

