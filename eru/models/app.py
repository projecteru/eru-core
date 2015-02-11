#!/usr/bin/python
#coding:utf-8

from werkzeug.utils import cached_property

from eru.models import db, Base
from eru.models.appconfig import AppConfig, ResourceConfig
from datetime import datetime

class Version(Base):
    __tablename__ = 'version'

    sha = db.Column(db.CHAR(40), index=True, nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'))
    created = db.Column(db.DateTime, default=datetime.now)

    containers = db.relationship('Container', backref='version', lazy='dynamic')
    tasks = db.relationship('Task', backref='version', lazy='dynamic')
    application = db.relationship('App', foreign_keys=[app_id])

    def __init__(self, app_id, sha):
        self.app_id = app_id
        self.sha = sha

    @classmethod
    def get_by_app_and_version(cls, application, sha):
        return cls.query.filter(cls.sha.like('%{}%'.format(sha)), cls.app_id == application.id).one()

    @property
    def name(self):
        return self.application.name

    @cached_property
    def appconfig(self):
        return AppConfig.get_by_name_and_version(self.name, self.short_sha)

    @property
    def short_sha(self):
        return self.sha[:7]

    def get_resource_config(self, env='prod'):
        return ResourceConfig.get_by_name_and_env(self.name, env)


class App(Base):
    __tablename__ = 'app'

    name = db.Column(db.CHAR(32), nullable=False, unique=True)
    git = db.Column(db.String(255), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
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

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id == id).one()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).one()

    def get_version(self, version):
        return self.versions.filter(Version.sha.like('%{}%'.format(version))).first()

