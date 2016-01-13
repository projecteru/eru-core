# coding:utf-8

import json
import cPickle
import requests
import itertools
import sqlalchemy.exc
from decimal import Decimal as D
from datetime import datetime

from eru.ipam import ipam
from eru.agent import get_agent
from eru.clients import rds
from eru.models import db
from eru.models.base import Base, PropsMixin, PropsItem
from eru.utils.decorator import EruJSONEncoder

_CONTAINER_PUB_KEY = 'container:%s'
_EIP_BOUND_KEY = 'eip:%s:container'

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

    callback_url = PropsItem('callback_url')
    eip = PropsItem('eip')

    def __init__(self, container_id, host, version, name, entrypoint, env):
        self.container_id = container_id
        self.host_id = host.id
        self.version_id = version.id
        self.app_id = version.app_id
        self.name = name
        self.entrypoint = entrypoint
        self.env = env

    def get_uuid(self):
        return '/eru/container/%s' % self.id

    @classmethod
    def create(cls, container_id, host, version, name,
            entrypoint, cores, env, nshare=0, callback_url=''):
        """创建一个容器. cores 是 {'full': [core, ...], 'part': [core, ...]}"""
        try:
            container = cls(container_id, host, version, name, entrypoint, env)
            db.session.add(container)
            host.count = host.__class__.count - \
                    D(len(cores.get('full', []))) - \
                    D(format(D(nshare) / D(host.core_share), '.3f'))
            db.session.add(host)
            db.session.commit()

            cores['nshare'] = nshare
            container.cores = cores
            container.callback_url = callback_url

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

    @classmethod
    def delete_by_container_id(cls, cid):
        cls.query.filter_by(container_id=cid).delete()
        db.session.commit()

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

    def get_entry(self):
        appconfig = self.version.appconfig
        return appconfig.entrypoints.get(self.entrypoint, {})

    def get_ports(self):
        appconfig = self.version.appconfig
        if self.entrypoint not in appconfig.entrypoints:
            return []

        entry = appconfig.entrypoints[self.entrypoint]
        ports = entry.get('ports', [])
        return [int(p.split('/')[0]) for p in ports]

    def get_backends(self):
        """daemon的话是个空列表"""
        if self.network_mode == 'host':
            ips = [self.host.ip]
        else:
            ips = ipam.get_ip_by_container(self.container_id)
            ips = [str(ip) for ip in ips]
        ports = self.get_ports()
        return ['{0}:{1}'.format(ip, port) for ip, port in itertools.product(ips, ports)]

    def delete(self):
        """删除这条记录, 记得要释放自己占用的资源"""
        # release ip
        ipam.release_ip_by_container(self.container_id)
        # release eip
        self.release_eip()

        # release core and increase core count
        host = self.host
        cores = self.cores
        host.release_cores(cores, cores.get('nshare', 0))
        del self.cores
        host.count = host.__class__.count + \
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
        ips = ipam.get_ip_by_container(self.container_id)
        d.update(
            host=self.host.addr.split(':')[0],
            hostname=self.host.name,
            cores={
                'full': [c.label for c in self.full_cores],
                'part': [c.label for c in self.part_cores],
                'nshare': self.cores.get('nshare', 0),
            },
            version=self.version.short_sha,
            networks=ips,
            backends=self.get_backends(),
            appname=self.appname,
            eip=self.eip,
        )
        return d

    def bind_eip(self, eip=None):
        if self.eip:
            return

        if eip is None:
            for e in self.host.eips:
                if not check_eip_bound(e):
                    eip = e
                    break

        if eip is None:
            return

        agent = get_agent(self.host)
        agent.publish_container(eip, self)
        self.eip = eip
        set_eip_bound(eip, self.container_id)
        return True

    def release_eip(self):
        if not self.eip:
            return
        agent = get_agent(self.host)
        agent.unpublish_container(self.eip, self)
        del self.eip
        clean_eip_bound(self.eip)
        return True


def check_eip_bound(eip):
    return bool(rds.get(_EIP_BOUND_KEY % eip))


def set_eip_bound(eip, container_id):
    rds.set(_EIP_BOUND_KEY % eip, container_id)


def clean_eip_bound(eip):
    rds.delete(_EIP_BOUND_KEY % eip)
