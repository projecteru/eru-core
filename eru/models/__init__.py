#!/usr/bin/python
# encoding: UTF-8

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declared_attr

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    db.app = app
    db.create_all()

class Base(db.Model):

    __abstract__ = True

    @declared_attr
    def id(cls):
        return db.Column('id', db.Integer, primary_key=True, autoincrement=True)

from eru.models.host import Cpu, Port, Host
from eru.models.pod import Pod
from eru.models.group import Group, GroupPod
from eru.models.app import App, Version
from eru.models.container import Container
from eru.models.resource import MySQL, InfluxDB

__all__ = [
    'db', 'Base', 'Cpu', 'Port', 'Host', 'Pod', 'Group', 'GroupPod',
    'App', 'Version', 'Container', 'MySQL', 'InfluxDB',
]
