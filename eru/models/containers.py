#!/usr/bin/python
#coding:utf-8

from eru.models import db
from datetime import datetime

class Containers(db.Model):
    __tablename__ = 'containers'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    hid = db.Column(db.Integer, db.ForeignKey('hosts.id'))
    cid = db.Column(db.Integer, db.ForeignKey('cpus.id'))
    aid = db.Column(db.Integer, db.ForeignKey('apps.id'))
    pid = db.Column(db.Integer, db.ForeignKey('ports.id'))
    vid = db.Column(db.Integer, db.ForeignKey('versions.id'))
    container_id = db.Column(db.CHAR(64), nullable=False, unique=True)
    name = db.Column(db.CHAR(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, container_id):
        self.container_id = container_id

