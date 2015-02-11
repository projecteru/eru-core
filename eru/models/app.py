#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc
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

    def __init__(self, sha, app_id):
        self.sha = sha
        self.app_id = app_id

    @classmethod
    def create(cls, sha, app_id):
        try:
            version = cls(sha, app_id)
            db.session.add(version)
            db.session.commit()
            return version
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_app_and_version(cls, application, sha):
        return cls.query.filter(cls.sha.like('%{}%'.format(sha)), cls.app_id == application.id).one()

    @property
    def name(self):
        return self.app.name

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
    def get_or_create(cls, name, git, token):
        app = cls.query.filter(cls.name == name).first()
        if app:
            return app
        try:
            app = cls(name, git, token)
            db.session.add(app)
            db.session.commit()
            return app
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id == id).one()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).one()

    def get_version(self, version):
        return self.versions.filter(Version.sha.like('%{}%'.format(version))).first()

    def add_version(self, sha):
        version = Version.create(sha, self.id)
        if not version:
            return False
        self.versions.append(version)
        db.session.add(self)
        db.session.commit()
        return True

    def assigned_to_group(self, group):
        if not group:
            return False
        group.apps.append(self)
        db.session.add(group)
        db.session.commit()
        return True
