# coding:utf-8

import json
import cPickle
import requests
import itertools
import sqlalchemy.exc
from decimal import Decimal as D
from datetime import datetime

from eru.clients import rds
from eru.models import db
from eru.models.base import Base, PropsMixin
from eru.utils.decorator import EruJSONEncoder

_CONTAINER_PUB_KEY = 'container:%s'

class Container(Base, PropsMixin):
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
            entrypoint, cores, env, nshare=0, callback_url=''):
        """创建一个容器. cores 是 {'full': [core, ...], 'part': [core, ...]}"""
        from .host import Host
        try:
            container = cls(container_id, host, version, name, entrypoint, env)
            db.session.add(container)
            host.count = Host.count - \
                    D(len(cores.get('full', []))) - \
                    D(format(D(nshare) / D(host.core_share), '.3f'))
            db.session.add(host)
            db.session.commit()

            cores['nshare'] = nshare
            container.cores = cores
            container.set_props(callback_url=callback_url)

            rds.publish(_CONTAINER_PUB_KEY % name.split('_')[0],
                json.dumps({'container': container_id, 'status': 'create'}))
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
        return self.name.rsplit('_', 2)[0]

    @property
    def network_mode(self):
        appconfig = self.version.appconfig
        return appconfig.entrypoints.get(self.entrypoint, {}).get('network_mode', 'bridge')

    @property
    def meta(self):
        """一定会加入__version__这个变量, 7位的git sha1值"""
        m = self.version.appconfig.get('meta', {})
        m['__version__'] = self.version.short_sha
        return m

    @property
    def ident_id(self):
        return self.name.rsplit('_', 2)[-1]

    @property
    def _cores_key(self):
        return 'eru:container:%s:cores' % self.id

    def _get_cores(self):
        try:
            return cPickle.loads(rds.get(self._cores_key))
        except (EOFError, TypeError):
            return {}
    def _set_cores(self, cores):
        rds.set(self._cores_key, cPickle.dumps(cores))
    def _del_cores(self):
        rds.delete(self._cores_key)

    cores = property(_get_cores, _set_cores, _del_cores)
    del _get_cores, _set_cores, _del_cores

    @property
    def full_cores(self):
        return self.cores.get('full', [])

    @property
    def part_cores(self):
        return self.cores.get('part', [])

    def get_ports(self):
        appconfig = self.version.appconfig
        if self.entrypoint not in appconfig.entrypoints:
            return []

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
        from .host import Host
        # release ip
        [ip.release() for ip in self.ips]
        # release core and increase core count
        host = self.host
        cores = self.cores
        host.release_cores(cores, cores.get('nshare', 0))
        del self.cores
        host.count = Host.count + \
                D(len(cores.get('full', []))) + \
                D(format(D(cores.get('nshare', 0)) / D(host.core_share), '.3f'))
        db.session.add(host)
        # remove container
        db.session.delete(self)
        db.session.commit()
        rds.publish(_CONTAINER_PUB_KEY % self.appname,
            json.dumps({'container': self.container_id, 'status': 'delete'}))

    def kill(self):
        self.is_alive = 0
        db.session.add(self)
        db.session.commit()
        rds.publish(_CONTAINER_PUB_KEY % self.appname,
            json.dumps({'container': self.container_id, 'status': 'down'}))

    def cure(self):
        self.is_alive = 1
        db.session.add(self)
        db.session.commit()
        rds.publish(_CONTAINER_PUB_KEY % self.appname,
            json.dumps({'container': self.container_id, 'status': 'up'}))

    def callback_report(self, **kwargs):
        """调用创建的时候设置的回调url, 失败就不care了"""
        callback_url = self.props.get('callback_url', '')
        if not callback_url:
            return

        data = self.to_dict()
        data.update(**kwargs)

        try:
            requests.post(callback_url, data=json.dumps(data, cls=EruJSONEncoder),
                    timeout=5, headers={'content-type': 'application/json'})
        except:
            pass

    def to_dict(self):
        d = super(Container, self).to_dict()
        d.update(
            host=self.host.addr.split(':')[0],
            cores={
                'full': [c.label for c in self.full_cores],
                'part': [c.label for c in self.part_cores],
                'nshare': self.cores.get('nshare', 0),
            },
            version=self.version.short_sha,
            networks=self.ips.all(),
            backends=self.get_backends(),
        )
        return d
