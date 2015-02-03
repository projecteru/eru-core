#!/usr/bin/python
#coding:utf-8

from eru.models import db
from datetime import datetime

class Versions(db.Model):
    __tablename__ = 'versions'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    sha = db.Column(db.CHAR(40), index=True, nullable=False)
    aid = db.Column(db.Integer, db.ForeignKey('apps.id'))
    created = db.Column(db.DateTime, default=datetime.now)

    containers = db.relationship('Containers', backref='version', lazy='dynamic')

    def __init__(self, sha):
        self.sha = sha

class Apps(db.Model):
    __tablename__ = 'apps'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.CHAR(32), nullable=False, unique=True)
    git = db.Column(db.String(255), nullable=False)
    gid = db.Column(db.Integer, db.ForeignKey('groups.id'))
    update = db.Column(db.DateTime, default=datetime.now)

    #TODO FK to resource

    versions = db.relationship('Versions', backref='app', lazy='dynamic')
    containers = db.relationship('Containers', backref='app', lazy='dynamic')
    mysql = db.relationship('MySQL', backref='app', lazy='dynamic')
    influxdb = db.relationship('InfluxDB', backref='app', lazy='dynamic')

    def __init__(self, name, git):
        self.name = name
        self.git = git

