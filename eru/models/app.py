#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc
from datetime import datetime
from werkzeug.utils import cached_property

from eru.models import db
from eru.models.base import Base
from eru.models.appconfig import AppConfig, ResourceConfig


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
        return cls.query.filter(cls.sha.like('{}%'.format(sha)), cls.app_id == application.id).one()

    @property
    def name(self):
        return self.app.name

    @cached_property
    def appconfig(self):
        return AppConfig.get_by_name_and_version(self.name, self.short_sha)

    @property
    def short_sha(self):
        return self.sha[:7]

    @property
    def user_id(self):
        return self.app.user_id

    def get_resource_config(self, env='prod'):
        return ResourceConfig.get_by_name_and_env(self.name, env)

    def get_ports(self, entrypoint):
        entry = self.appconfig.entrypoints.get(entrypoint, {})
        ports = entry.get('ports', [])
        return [int(p.split('/')[0]) for p in ports]

    def to_dict(self):
        d = super(Version, self).to_dict()
        d['name'] = self.name
        d['appconfig'] = self.appconfig.to_dict()
        return d


class App(Base):
    __tablename__ = 'app'

    name = db.Column(db.CHAR(32), nullable=False, unique=True)
    git = db.Column(db.String(255), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    token = db.Column(db.CHAR(32), nullable=False, unique=True)
    update = db.Column(db.DateTime, default=datetime.now)
    _user_id = db.Column(db.Integer, nullable=False, default=0)

    versions = db.relationship('Version', backref='app', lazy='dynamic')
    containers = db.relationship('Container', backref='app', lazy='dynamic')
    tasks = db.relationship('Task', backref='app', lazy='dynamic')

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
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @property
    def user_id(self):
        """默认使用id, 如果不对可以通过_user_id手动纠正."""
        return self._user_id or self.id

    def get_version(self, version):
        return self.versions.filter(Version.sha.like('{}%'.format(version))).first()

    def get_resource_config(self, env='prod'):
        return ResourceConfig.get_by_name_and_env(self.name, env)

    def list_resource_config(self):
        return ResourceConfig.list_env(self.name)

    def list_versions(self, start=0, limit=20):
        q = self.versions.order_by(Version.id.desc()).offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def add_version(self, sha):
        version = Version.create(sha, self.id)
        if not version:
            return None
        self.versions.append(version)
        db.session.add(self)
        db.session.commit()
        return version

    def assigned_to_group(self, group):
        if not group:
            return False
        group.apps.append(self)
        db.session.add(group)
        db.session.commit()
        return True

