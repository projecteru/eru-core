#!/usr/bin/python
#coding:utf-8

from datetime import datetime
from eru.models import db, Base

class Container(Base):
    __tablename__ = 'container'

    hid = db.Column(db.Integer, db.ForeignKey('host.id'))
    cid = db.Column(db.Integer, db.ForeignKey('cpu.id'))
    aid = db.Column(db.Integer, db.ForeignKey('app.id'))
    pid = db.Column(db.Integer, db.ForeignKey('port.id'))
    vid = db.Column(db.Integer, db.ForeignKey('version.id'))
    container_id = db.Column(db.CHAR(64), nullable=False, unique=True)
    name = db.Column(db.CHAR(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, container_id):
        self.container_id = container_id

