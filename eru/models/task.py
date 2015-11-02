# coding: utf-8

import sqlalchemy.exc
from datetime import datetime

from eru.models import db
from eru.models.base import Base, PropsMixin, PropsItem
from eru.consts import (
    ERU_TASK_RESULTKEY,
    ERU_TASK_LOGKEY,
    ERU_TASK_PUBKEY,
    TASK_ACTIONS,
    TASK_RESULTS,
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

    reason = PropsItem('reason', default='')
    container_ids = PropsItem('container_ids', default=[])

    def __init__(self, host_id, app_id, version_id, type_):
        self.host_id = host_id
        self.app_id = app_id
        self.version_id = version_id
        self.type = type_

    def get_uuid(self):
        return '/eru/task/%s' % self.id

    @classmethod
    def create(cls, type_, version, host, props={}):
        try:
            task = cls(host.id, version.app_id, version.id, type_)
            db.session.add(task)
            db.session.commit()
            task.set_props(props)
            return task
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    def finish(self, result):
        self.finished = datetime.now()
        self.result = result
        db.session.add(self)
        db.session.commit()

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
            result=TASK_RESULTS.get(self.result, 'unkown'),
            name=self.app.name,
            version=self.version.short_sha,
            host=self.host.ip,
        )
        return d
