#!/usr/bin/python
#coding:utf-8

import json
import sqlalchemy.exc
from datetime import datetime

from eru.models import db
from eru.models.base import Base
from eru.common.settings import ERU_TASK_RESULTKEY

class Task(Base):
    __tablename__ = 'task'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'))
    version_id = db.Column(db.Integer, db.ForeignKey('version.id'))
    type = db.Column(db.Integer, nullable=False)
    result = db.Column(db.Integer, nullable=True)
    finished = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)
    properties = db.Column(db.String(512), default='{}')

    def __init__(self, host_id, app_id, version_id, type_, props):
        self.host_id = host_id
        self.app_id = app_id
        self.version_id = version_id
        self.type = type_
        self.properties = json.dumps(props)

    @classmethod
    def create(cls, type_, version, host, props={}):
        try:
            task = cls(host.id, version.app_id, version.id, type_, props)
            db.session.add(task)
            db.session.commit()
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

    def finish_with_result(self, result):
        self.finished = datetime.now()
        self.result = result
        db.session.add(self)
        db.session.commit()

    @property
    def props(self):
        return json.loads(self.properties)

    def set_props(self, key, value):
        p = self.props
        p[key] = value
        self.properties = json.dumps(p)
        db.session.add(self)
        db.session.commit()

    @property
    def result_key(self):
        return ERU_TASK_RESULTKEY % self.id 

