#!/usr/bin/python
# encoding: UTF-8

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from eru.models.hosts import Cpus, Ports, Hosts
from eru.models.pods import Pods
from eru.models.groups import Groups, GroupPod
from eru.models.apps import Apps, Versions
from eru.models.containers import Containers
from eru.models.resource import MySQL, InfluxDB

def init_db(app):
    db.init_app(app)
    db.app = app
    db.create_all()

__all__ = [
    'db', 'Cpus', 'Ports', 'Hosts', 'Pods', 'Groups', 'GroupPod',
    'Apps', 'Versions', 'Containers', 'MySQL', 'InfluxDB',
]
