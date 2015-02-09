#!/usr/bin/python
#coding:utf-8

from datetime import datetime
from eru.models import db, Base

class Task(Base):
    __tablename__ = 'task'

    hid = db.Column(db.Integer, db.ForeignKey('host.id'))
    aid = db.Column(db.Integer, db.ForeignKey('app.id'))
    vid = db.Column(db.Integer, db.ForeignKey('version.id'))
    typ = db.Column(db.Integer, nullable=False)
    result = db.Column(db.Integer, nullable=True)
    finished = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, typ):
        self.typ = typ

    def finish(self):
        self.finished = datetime.now()

    def set_result(self, result):
        self.result = result

    @property
    def host(self):
        from .host import Host
        return Host.get(self.hid)

    @property
    def version(self):
        from .app import Version
        return Version.get(self.vid)
