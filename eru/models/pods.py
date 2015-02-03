#!/usr/bin/python
#coding:utf-8

from eru.models import db

class Pods(db.Model):
    __tablename__ = 'pods'

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.CHAR(30), nullable=False)
    description = db.Column(db.Text)

    hosts = db.relationship('Hosts', backref='pod', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description

