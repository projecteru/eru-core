#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc
from datetime import datetime

from eru.models import db, Base


class Container(Base):
    __tablename__ = 'container'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'))
    version_id = db.Column(db.Integer, db.ForeignKey('version.id'))
    container_id = db.Column(db.CHAR(64), nullable=False, unique=True)
    name = db.Column(db.CHAR(255), nullable=False)
    entrypoint = db.Column(db.CHAR(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)
    is_alive = db.Column(db.Integer, default=1)

    cores = db.relationship('Core', backref='container', lazy='dynamic')
    port = db.relationship('Port', backref='container', lazy='dynamic')

    def __init__(self, container_id, host, version, name, entrypoint):
        self.container_id = container_id
        self.host_id = host.id
        self.version_id = version.id
        self.app_id = version.app_id
        self.name = name
        self.entrypoint = entrypoint

    @classmethod
    def create(cls, container_id, host, version, name, entrypoint, cores, port=None):
        """
        创建一个容器. cores 是 [core, core, ...] port 则是 port.
        """
        try:
            container = cls(container_id, host, version, name, entrypoint)
            db.session.add(container)
            for core in cores:
                container.cores.append(core)
            if port:
                container.ports.append(port)
            db.session.commit()
            return container
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_containers_by_host(cls, host):
        return cls.query.filter(cls.host_id == host.id).all()

    def delete(self):
        """删除这条记录, 记得要释放自己占用的资源"""
        host = self.host
        host.release_cores(self.cores.all())
        host.release_ports(self.port.all())
        db.session.delete(self)
        db.session.commit()

    def not_alive(self):
        self.is_alive = 0
        db.session.add(self)
        db.session.commit()

