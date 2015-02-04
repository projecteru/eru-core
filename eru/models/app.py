#!/usr/bin/python
#coding:utf-8

from eru.models import db, Base
from datetime import datetime

class Version(Base):
    __tablename__ = 'version'

    sha = db.Column(db.CHAR(40), index=True, nullable=False)
    aid = db.Column(db.Integer, db.ForeignKey('app.id'))
    created = db.Column(db.DateTime, default=datetime.now)

    containers = db.relationship('Container', backref='version', lazy='dynamic')
    tasks = db.relationship('Task', backref='version', lazy='dynamic')

    def __init__(self, sha):
        self.sha = sha

class App(Base):
    __tablename__ = 'app'

    name = db.Column(db.CHAR(32), nullable=False, unique=True)
    git = db.Column(db.String(255), nullable=False)
    gid = db.Column(db.Integer, db.ForeignKey('group.id'))
    token = db.Column(db.CHAR(32), nullable=False, unique=True)
    update = db.Column(db.DateTime, default=datetime.now)

    #TODO FK to more resource

    versions = db.relationship('Version', backref='app', lazy='dynamic')
    containers = db.relationship('Container', backref='app', lazy='dynamic')
    tasks = db.relationship('Task', backref='app', lazy='dynamic')
    mysql = db.relationship('MySQL', backref='app', lazy='dynamic')
    influxdb = db.relationship('InfluxDB', backref='app', lazy='dynamic')

    def __init__(self, name, git, token):
        self.name = name
        self.git = git
        self.token = token

