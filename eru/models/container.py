#!/usr/bin/python
#coding:utf-8

import itertools
import sqlalchemy.exc
from datetime import datetime

from eru.models import db
from eru.models.base import Base

class Container(Base):
    __tablename__ = 'container'

    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'))
    version_id = db.Column(db.Integer, db.ForeignKey('version.id'))
    container_id = db.Column(db.CHAR(64), nullable=False, index=True)
    name = db.Column(db.CHAR(255), nullable=False)
    entrypoint = db.Column(db.CHAR(255), nullable=False)
    env = db.Column(db.CHAR(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)
    is_alive = db.Column(db.Integer, default=1)

    cores = db.relationship('Core', backref='container', lazy='dynamic')
    ips = db.relationship('IP', backref='container', lazy='dynamic')

    def __init__(self, container_id, host, version, name, entrypoint, env):
        self.container_id = container_id
        self.host_id = host.id
        self.version_id = version.id
        self.app_id = version.app_id
        self.name = name
        self.entrypoint = entrypoint
        self.env = env

    @classmethod
    def create(cls, container_id, host, version, name,
            entrypoint, cores, env):
        """
        创建一个容器. cores 是 [core, core, ...].
        ips是string
        """
        try:
            container = cls(container_id, host, version, name, entrypoint, env)
            db.session.add(container)
            host.count += 1
            db.session.add(host)
            for core in cores:
                container.cores.append(core)
            db.session.commit()
            return container
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_multi_by_host(cls, host):
        return cls.query.filter(cls.host_id == host.id).all()

    @classmethod
    def get_by_container_id(cls, cid):
        return cls.query.filter(cls.container_id.like('{}%'.format(cid))).first()

    @property
    def appname(self):
        return self.name.split('_')[0]

    def get_ports(self):
        appconfig = self.version.appconfig
        entry = appconfig.entrypoints[self.entrypoint]
        ports = entry.get('ports', [])
        return [int(p.split('/')[0]) for p in ports]

    def get_ips(self):
        return [str(ip) for ip in self.ips]

    def get_backends(self):
        """daemon的话是个空列表"""
        ips = self.get_ips()
        ports = self.get_ports()
        return ['{0}:{1}'.format(ip, port) for ip, port in itertools.product(ips, ports)]

    def transform(self, version, cid, name):
        """变身!
        更新容器的时候需要让这个容器修改一下
        修改这个容器, 用新的version, cid, ports, cid来替换.
        版本, 端口, 容器的id一定会更新.
        """
        # 核不需要释放, 继续复用原有的
        # 新的属性设置上去
        self.version_id = version.id
        self.container_id = cid
        self.name = name
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """删除这条记录, 记得要释放自己占用的资源"""
        # release ip
        [ip.release() for ip in self.ips]
        # release core
        host = self.host
        host.release_cores(self.cores.all())
        host.count -= 1
        db.session.add(host)
        # remove container
        db.session.delete(self)
        db.session.commit()

    def kill(self):
        self.is_alive = 0
        db.session.add(self)
        db.session.commit()

    def cure(self):
        self.is_alive = 1
        db.session.add(self)
        db.session.commit()

    def to_dict(self):
        d = super(Container, self).to_dict()
        d.update(
            host=self.host.addr.split(':')[0],
            cores=[c.label for c in self.cores.all()],
            version=self.version.short_sha,
            networks=self.ips.all(),
        )
        return d

