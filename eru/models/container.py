#!/usr/bin/python
# coding:utf-8

import cPickle
import itertools
import sqlalchemy.exc
from datetime import datetime

from eru.common.clients import rds
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
    # 默认 40m, 最小单位为 k
    memory = db.Column(db.Integer, nullable=False, default=40960)
    env = db.Column(db.CHAR(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)
    is_alive = db.Column(db.Integer, default=1)

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
            entrypoint, cores, env, nshare=0):
        """
        创建一个容器. cores 是 {'full': [core, core, ...], 'part': [core, core, ...]}
        ips是string
        """
        try:
            container = cls(container_id, host, version, name, entrypoint, env)
            db.session.add(container)
            host.count += 1
            db.session.add(host)
            db.session.commit()

            cores['nshare'] = nshare
            container.cores = cores
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

    @property
    def ident_id(self):
        return self.name.split('_')[-1]

    @property
    def _cores_key(self):
        return 'eru:container:%s:cores' % self.id

    @property
    def cores(self):
        try:
            return cPickle.loads(rds.get(self._cores_key))
        except (EOFError, TypeError):
            return {}

    @cores.setter
    def cores(self, cores):
        rds.set(self._cores_key, cPickle.dumps(cores))

    @cores.deleter
    def cores(self):
        rds.delete(self._cores_key)

    @property
    def full_cores(self):
        return self.cores.get('full', [])

    @property
    def part_cores(self):
        return self.cores.get('part', [])

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

    def delete(self):
        """删除这条记录, 记得要释放自己占用的资源"""
        # release ip
        [ip.release() for ip in self.ips]
        # release core
        host = self.host
        host.release_cores(self.cores, self.cores['nshare'])
        del self.cores
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
            cores={
                'full': [c.label for c in self.full_cores],
                'part': [c.label for c in self.part_cores],
                'nshare': self.cores['nshare'],
            },
            version=self.version.short_sha,
            networks=self.ips.all(),
        )
        return d

