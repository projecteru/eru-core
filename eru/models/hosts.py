#!/usr/bin/python
#coding:utf-8

from eru.models import db

class Cpus(db.Model):
    __tablename__ = 'cpus'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    hid = db.Column(db.Integer, db.ForeignKey('hosts.id'))
    used = db.Column(db.Integer, default=0)

    def use(self):
        self.used = 1

    def release(self):
        self.uesd = 0


class Hosts(db.Model):
    __tablename__ = 'hosts'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    addr = db.Column(db.CHAR(30), nullable=False, unique=True)
    name = db.Column(db.CHAR(30), nullable=False)
    uid = db.Column(db.CHAR(60), nullable=False)
    ncpu = db.Column(db.Integer, nullable=False, default=0)
    mem = db.Column(db.BigInteger, nullable=False, default=0)

    containers = db.Column(db.Integer, default=0)

    gid = db.Column(db.Integer, db.ForeignKey('groups.id'))
    pid = db.Column(db.Integer, db.ForeignKey('pods.id'))
    cpus = db.relationship('Cpus', backref='host', lazy='dynamic')

    def __init__(self, addr, name, uid, ncpu, mem):
        self.addr = addr
        self.name = name
        self.uid = uid
        self.ncpu = ncpu
        self.mem = mem

