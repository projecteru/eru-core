# coding: utf-8

import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base

class GroupPod(db.Model):

    group_id = db.Column(db.ForeignKey('group.id'), primary_key=True)
    pod_id = db.Column(db.ForeignKey('pod.id'), primary_key=True)

class Group(Base):
    __tablename__ = 'group'

    name = db.Column(db.CHAR(30), nullable=False, unique=True)
    description = db.Column(db.Text)

    pods = db.relationship('Pod', secondary=GroupPod.__table__)
    apps = db.relationship('App', backref='group', lazy='dynamic')
    private_hosts = db.relationship('Host', backref='group', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description

    @classmethod
    def create(cls, name, description=''):
        try:
            group = cls(name, description)
            db.session.add(group)
            db.session.commit()
            return group
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @classmethod
    def list_all(cls, start=0, limit=20):
        q = cls.query.offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def list_pods(self, start=0, limit=20):
        q = self.pods
        return q[start:start+limit]

    def get_private_hosts(self, pod=None, start=0, limit=20):
        q = self.private_hosts
        if pod:
            q = q.filter_by(pod_id=pod.id).offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()
