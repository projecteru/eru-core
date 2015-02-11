#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc
from datetime import datetime
from eru.models import db, Base

class Task(Base):
    __tablename__ = 'task'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'))
    version_id = db.Column(db.Integer, db.ForeignKey('version.id'))
    type = db.Column(db.Integer, nullable=False)
    result = db.Column(db.Integer, nullable=True)
    finished = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)

    #host = db.relationship('Host', foreign_keys=[host_id])
    #app = db.relationship('App', foreign_keys=[app_id])
    #version = db.relationship('Version', foreign_keys=[version_id])

    def __init__(self, host_id, app_id, version_id, type_):
        self.host_id = host_id
        self.app_id = app_id
        self.version_id = version_id
        self.type_ = type_

    @classmethod
    def create(cls, type_, version, host):
        try:
            task = cls(host.id, version.app_id, version.id, type_)
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
        db.seesion.commit()

