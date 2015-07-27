# coding: utf-8

import sqlalchemy.exc
from datetime import datetime

from eru.models import db
from eru.models.base import Base, PropsMixin
from eru.consts import (
    ERU_TASK_RESULTKEY,
    ERU_TASK_LOGKEY,
    ERU_TASK_PUBKEY,
    TASK_ACTIONS,
)

class Task(Base, PropsMixin):
    __tablename__ = 'task'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'), index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('version.id'), index=True)
    type = db.Column(db.Integer, nullable=False)
    result = db.Column(db.Integer, nullable=True)
    finished = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, host_id, app_id, version_id, type_):
        self.host_id = host_id
        self.app_id = app_id
        self.version_id = version_id
        self.type = type_

    @classmethod
    def create(cls, type_, version, host, props={}):
        try:
            task = cls(host.id, version.app_id, version.id, type_)
            db.session.add(task)
            db.session.commit()
            task.set_props(**props)
            return task
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    def finish(self):
        self.finished = datetime.now()
        db.session.add(self)
        db.session.commit()

    def set_result(self, result):
        self.result = result
        db.session.add(self)
        db.session.commit()

    def finish_with_result(self, result, **kw):
        self.finished = datetime.now()
        db.session.add(self)
        db.session.commit()
        self.result = result

        if kw:
            self.set_props(**kw)

    @property
    def publish_key(self):
        return ERU_TASK_PUBKEY % self.id

    @property
    def log_key(self):
        return ERU_TASK_LOGKEY % self.id

    @property
    def result_key(self):
        return ERU_TASK_RESULTKEY % self.id 

    def to_dict(self):
        d = super(Task, self).to_dict()
        d.update(
            props=self.props,
            action=TASK_ACTIONS.get(self.type, 'unkown'),
            name=self.app.name,
            version=self.version.short_sha,
            host=self.host.ip,
        )
        d.pop('properties', '')
        return d

