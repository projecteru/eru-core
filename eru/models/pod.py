#!/usr/bin/python
#coding:utf-8

from eru.models import db, Base

class Pod(Base):
    __tablename__ = 'pod'

    name = db.Column(db.CHAR(30), nullable=False, unique=True)
    description = db.Column(db.Text)

    hosts = db.relationship('Host', backref='pod', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description

    @classmethod
    def get(cls, id):
        return cls.query.filter(cls.id==id).one()
