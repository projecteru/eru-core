#!/usr/bin/python
#coding:utf-8

from eru.models import db, Base

class GroupPod(db.Model):
    gid = db.Column(db.ForeignKey('group.id'), primary_key=True)
    pid = db.Column(db.ForeignKey('pod.id'), primary_key=True)

class Group(Base):
    __tablename__ = 'group'

    name = db.Column(db.CHAR(30), nullable=False, unique=True)
    description = db.Column(db.Text)

    pods = db.relationship('Pod', secondary=GroupPod.__table__)
    hosts = db.relationship('Host', backref='group', lazy='dynamic')
    apps = db.relationship('App', backref='group', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description

