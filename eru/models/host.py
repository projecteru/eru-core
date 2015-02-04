#!/usr/bin/python
#coding:utf-8

from eru.models import db, Base

class Port(Base):
    __tablename__ = 'port'

    hid = db.Column(db.Integer, db.ForeignKey('host.id'))
    used = db.Column(db.Integer, default=0)
    port = db.Column(db.Integer, nullable=False)

    containers = db.relationship('Container', backref='port', lazy='dynamic')

    def __init__(self, port):
        self.port = port

    def use(self):
        self.used = 1


class Cpu(Base):
    __tablename__ = 'cpu'

    hid = db.Column(db.Integer, db.ForeignKey('host.id'))
    used = db.Column(db.Integer, default=0)

    container = db.relationship('Container', backref='cpus', lazy='dynamic')

    def use(self):
        self.used = 1


class Host(Base):
    __tablename__ = 'host'

    addr = db.Column(db.CHAR(30), nullable=False, unique=True)
    name = db.Column(db.CHAR(30), nullable=False)
    uid = db.Column(db.CHAR(60), nullable=False)
    ncpu = db.Column(db.Integer, nullable=False, default=0)
    mem = db.Column(db.BigInteger, nullable=False, default=0)

    gid = db.Column(db.Integer, db.ForeignKey('group.id'))
    pid = db.Column(db.Integer, db.ForeignKey('pod.id'))

    cpus = db.relationship('Cpu', backref='host', lazy='dynamic')
    ports = db.relationship('Port', backref='host', lazy='dynamic')
    tasks = db.relationship('Task', backref='host', lazy='dynamic')
    containers = db.relationship('Container', backref='host', lazy='dynamic')

    def __init__(self, addr, name, uid, ncpu, mem):
        self.addr = addr
        self.name = name
        self.uid = uid
        self.ncpu = ncpu
        self.mem = mem

