#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base


class Core(Base):
    __tablename__ = 'core'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    label = db.Column(db.CHAR(10))
    used = db.Column(db.Integer, default=0)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))

    def __init__(self, label):
        self.label = label

    def is_free(self):
        return self.used < self.host.pod.core_share


class Host(Base):
    __tablename__ = 'host'

    addr = db.Column(db.CHAR(30), nullable=False, unique=True)
    name = db.Column(db.CHAR(30), nullable=False)
    uid = db.Column(db.CHAR(60), nullable=False)
    ncore= db.Column(db.Integer, nullable=False, default=0)
    mem = db.Column(db.BigInteger, nullable=False, default=0)
    count = db.Column(db.Integer, nullable=False, default=0)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    pod_id = db.Column(db.Integer, db.ForeignKey('pod.id'))
    is_alive = db.Column(db.Boolean, default=True)

    cores = db.relationship('Core', backref='host', lazy='dynamic')
    tasks = db.relationship('Task', backref='host', lazy='dynamic')
    containers = db.relationship('Container', backref='host', lazy='dynamic')

    def __init__(self, addr, name, uid, ncore, mem, pod_id):
        self.addr = addr
        self.name = name
        self.uid = uid
        self.ncore = ncore
        self.mem = mem
        self.pod_id = pod_id

    @classmethod
    def create(cls, pod, addr, name, uid, ncore, mem):
        """创建必须挂在一个 pod 下面"""
        if not pod:
            return None
        try:
            host = cls(addr, name, uid, ncore, mem, pod.id)
            for i in xrange(ncore):
                host.cores.append(Core(str(i)))
            db.session.add(host)
            db.session.commit()
            return host
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_addr(cls, addr):
        return cls.query.filter(cls.addr == addr).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @property
    def ip(self):
        return self.addr.split(':', 1)[0]

    def get_free_cores(self):
        #TODO 用 SQL 查询解决啊
        full_cores, part_cores = [], []
        for c in self.cores.all():
            if not c.used:
                full_cores.append(c)
            elif c.used < self.pod.core_share:
                part_cores.append(c)
        return full_cores, part_cores

    def get_filtered_containers(self, version=None, entrypoint=None, app=None, start=0, limit=20):
        q = self.containers
        if version is not None:
            q = q.filter_by(version_id=version.id)
        if entrypoint is not None:
            q = q.filter_by(entrypoint=entrypoint)
        if app is not None:
            q = q.filter_by(app_id=app.id)
        return q.offset(start).limit(limit).all()

    def get_containers_by_version(self, version):
        return self.containers.filter_by(version_id=version.id).all()

    def get_containers_by_app(self, app):
        return self.containers.filter_by(app_id=app.id).all()

    def assigned_to_group(self, group):
        """分配给 group, 那么这个 host 被标记为这个 group 私有"""
        if not group:
            return False
        group.private_hosts.append(self)
        db.session.add(group)
        db.session.commit()
        return True

    def occupy_cores(self, cores, nshare):
        for core in cores.get('full', []):
            core.used = self.pod.core_share
            db.session.add(core)

        for core in cores.get('part', []):
            core.used = core.used + nshare
            db.session.add(core)

        db.session.commit()

    def release_cores(self, cores, nshare):
        for core in cores.get('full', []):
            core.used = 0
            db.session.add(core)
        for core in cores.get('part', []):
            # 控制原子性
            core.used = Core.used - nshare
            db.session.add(core)
        db.session.commit()

    def kill(self):
        self.is_alive = False
        db.session.add(self)
        db.session.commit()

    def cure(self):
        self.is_alive = True
        db.session.add(self)
        db.session.commit()
