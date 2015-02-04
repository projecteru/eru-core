#!/usr/bin/python
#coding:utf-8

from datetime import datetime
from eru.models import db, Base

class Task(Base):
    __tablename__ = 'task'

    token = db.Column(db.CHAR(32), nullable=False, unique=True)
    hid = db.Column(db.Integer, db.ForeignKey('host.id'))
    aid = db.Column(db.Integer, db.ForeignKey('app.id'))
    vid = db.Column(db.Integer, db.ForeignKey('version.id'))
    typ = db.Column(db.Integer, nullable=False)
    result = db.Column(db.Integer, nullable=True)
    finished = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, token, typ):
        self.token = token
        self.typ = typ

    def finish(self):
        self.finished = datetime.now()

    def set_result(self, result):
        self.result = result

