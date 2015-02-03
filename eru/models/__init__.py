#!/usr/bin/python
# encoding: UTF-8

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from eru.models.hosts import Cpus, Hosts
from eru.models.pods import Pods
from eru.models.groups import Groups, GroupPod

def init_db(app):
    db.init_app(app)
    db.app = app
    db.create_all()

__all__ = [
    'db', 'Cpus', 'Hosts', 'Pods', 'Groups', 'GroupPod',
]
