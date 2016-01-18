# coding:utf-8

import random
import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base
from eru.config import DEFAULT_CORE_SHARE, DEFAULT_MAX_SHARE_CORE


class Pod(Base):
    __tablename__ = 'pod'

    name = db.Column(db.CHAR(30), nullable=False, unique=True)
    core_share = db.Column(db.Integer, nullable=False, default=DEFAULT_CORE_SHARE)
    max_share_core = db.Column(db.Integer, nullable=False, default=DEFAULT_MAX_SHARE_CORE)
    description = db.Column(db.Text)

    hosts = db.relationship('Host', backref='pod', lazy='dynamic')

    def __init__(self, name, description, core_share, max_share_core):
        self.name = name
        self.core_share = core_share
        self.max_share_core = max_share_core
        self.description = description

    @classmethod
    def create(cls, name, description='', core_share=DEFAULT_CORE_SHARE, max_share_core=DEFAULT_MAX_SHARE_CORE):
        try:
            pod = cls(name, description, core_share, max_share_core)
            db.session.add(pod)
            db.session.commit()
            return pod
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def list_all(cls, start=0, limit=20):
        q = cls.query.offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    def get_core_allocation(self, core_require):
        """按照core_share来分配core_require的独占/共享份数"""
        # TODO: 更细粒度的应该是把丫丢host上
        core_require = int(core_require * self.core_share)
        return core_require / self.core_share, core_require % self.core_share

    def list_hosts(self, start=0, limit=20, show_all=False):
        from .host import Host
        q = self.hosts
        if not show_all:
            q = q.filter_by(is_alive=True)
        q = q.order_by(Host.id.desc()).offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def get_free_public_hosts(self, limit):
        hosts = [h for h in self.hosts if h.is_public and h.is_alive]
        random.shuffle(hosts)
        return hosts[:limit] if limit is not None else hosts
 
    def get_private_hosts(self):
        return [h for h in self.hosts if not h.is_public and h.is_alive]

    def host_count(self):
        return self.hosts.count()

    def to_dict(self):
        d = super(Pod, self).to_dict()
        d['host_count'] = self.host_count()
        return d
