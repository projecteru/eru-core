#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc

import settings
from eru.models import db, Base

class Port(Base):
    __tablename__ = 'port'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    used = db.Column(db.Integer, default=0)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))
    port = db.Column(db.Integer, nullable=False)

    def __init__(self, port):
        self.port = port

    def is_used(self):
        return self.used == 1


class Core(Base):
    __tablename__ = 'core'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    label = db.Column(db.CHAR(10))
    used = db.Column(db.Integer, default=0)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))

    def __init__(self, label):
        self.label = label

    def is_used(self):
        return self.used == 1


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

    cores = db.relationship('Core', backref='host', lazy='dynamic')
    ports = db.relationship('Port', backref='host', lazy='dynamic')
    tasks = db.relationship('Task', backref='host', lazy='dynamic')
    containers = db.relationship('Container', backref='host', lazy='dynamic')
    #pod = db.relationship('Pod', foreign_keys=[pod_id])
    #group = db.relationship('Group', foreign_keys=[group_id])

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
            for i in xrange(settings.PORT_START, settings.PORT_START+ncore*settings.PORT_RANGE):
                host.ports.append(Port(i))
            db.session.add(host)
            db.session.commit()
            return host
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id == id).one()

    @classmethod
    def get_by_addr(cls, addr):
        return cls.query.filter(cls.addr == addr).one()

    def get_free_cores(self):
        return [c for c in self.cores.all() if not c.used]

    def get_free_ports(self, limit):
        return self.ports.filter_by(used=0).limit(limit).all()

    def assigned_to_group(self, group):
        """分配给 group, 那么这个 host 被标记为这个 group 私有"""
        if not group:
            return False
        group.private_hosts.append(self)
        db.session.add(group)
        db.session.commit()
        return True

    def occupy_cores(self, cores):
        for core in cores:
            core.used = 1
            db.session.add(core)
        db.session.commit()

    def occupy_ports(self, ports):
        for port in ports:
            port.used = 1
            db.session.add(port)
        db.session.commit()

    def release_cores(self, cores):
        for core in cores:
            core.used = 0
            db.session.add(core)
        db.session.commit()

    def release_ports(self, ports):
        for port in ports:
            port.used = 0
            db.session.add(port)
        db.session.commit()

