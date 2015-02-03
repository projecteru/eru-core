#!/usr/bin/python
#coding:utf-8

from eru.models import db

class GroupPod(db.Model):
    gid = db.Column(db.ForeignKey('groups.id'), primary_key=True)
    pid = db.Column(db.ForeignKey('pods.id'), primary_key=True)

class Groups(db.Model):
    __tablename__ = 'groups'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.CHAR(30), nullable=False)
    description = db.Column(db.Text)

    pods = db.relationship('Pods', secondary=GroupPod.__table__)

    def __init__(self, name, description):
        self.name = name
        self.description = description

