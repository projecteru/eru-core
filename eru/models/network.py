# coding: utf-8

import more_itertools
import sqlalchemy.exc
from netaddr import IPAddress, IPNetwork, AddrFormatError

from eru.clients import rds
from eru.models import db
from eru.models.base import Base
from eru.utils.decorator import redis_lock

class IPMixin(object):

    @property
    def address(self):
        return str(IPAddress(self.ipnum))

    @property
    def hostmask(self):
        return self.network.hostmask_string

    @property
    def vlan_address(self):
        """used for macvlan command"""
        return '{0}/{1}'.format(self.address, self.hostmask)

    @property
    def vlan_seq_id(self):
        """used for macvlan command seq, simply use network.id"""
        return self.network_id

    def __str__(self):
        return self.address

    def __int__(self):
        return self.ipnum

class IP(Base, IPMixin):

    __tablename__ = 'ip'

    ipnum = db.Column(db.Integer, nullable=False, default=0)
    vethname = db.Column(db.String(50), nullable=False, default='')
    network_id = db.Column(db.Integer, db.ForeignKey('network.id'))
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))

    def __init__(self, ipnum, network):
        self.ipnum = ipnum
        self.network_id = network.id

    @classmethod
    def create(cls, ipnum, network):
        ip = cls(ipnum, network)
        db.session.add(ip)
        db.session.commit()
        return ip

    def set_vethname(self, vethname):
        self.vethname = vethname
        db.session.add(self)
        db.session.commit()

    def assigned_to_container(self, container):
        if not container:
            return False
        container.ips.append(self)
        db.session.add(container)
        db.session.commit()
        return True

    def release(self):
        self.network.release_ip(self)
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        d = super(IP, self).to_dict()
        d.update(
            address=self.address,
            vlan_address=self.vlan_address,
        )
        return d

class VLanGateway(Base, IPMixin):

    __tablename__ = 'vlan_gateway'
    __table_args__  = (
        db.UniqueConstraint('network_id', 'host_id'),
    )

    ipnum = db.Column(db.Integer, nullable=False, default=0)
    network_id = db.Column(db.Integer, db.ForeignKey('network.id'))
    host_id = db.Column(db.Integer, db.ForeignKey('host.id'))

    def __init__(self, ipnum, network_id, host_id):
        self.ipnum = ipnum
        self.network_id = network_id
        self.host_id = host_id

    @classmethod
    def create(cls, ipnum, network_id, host_id):
        try:
            vg = cls(ipnum, network_id, host_id)
            db.session.add(vg)
            db.session.commit()
            return vg
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_host_and_network(cls, host_id, network_id):
        return cls.query.filter_by(network_id=network_id, host_id=host_id).first()

    @property
    def name(self):
        return 'vlan.%02d.br' % self.vlan_seq_id

    def release(self):
        self.network.release_gateway(self)
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        d = super(VLanGateway, self).to_dict()
        d.update(
            address=self.address,
            vlan_address=self.vlan_address,
            name=self.name,
        )
        return d

class Network(Base):

    __tablename__ = 'network'

    name = db.Column(db.CHAR(40), unique=True, nullable=False)
    netspace = db.Column(db.CHAR(40), nullable=False, default='', index=True)
    gateway_count = db.Column(db.Integer, nullable=False, default=100)

    ips = db.relationship('IP', backref='network', lazy='dynamic')
    gates = db.relationship('VLanGateway', backref='network', lazy='dynamic')

    def __init__(self, name, netspace, gateway_count):
        self.name = name
        self.netspace = netspace
        self.gateway_count = gateway_count

    @classmethod
    def create(cls, name, netspace, gateway_count=100):
        """create network and store ips(int) under this network in redis"""
        try:
            n = cls(name, netspace, gateway_count)
            db.session.add(n)
            db.session.commit()

            # create sub IPs
            network = n.network
            base = network.first

            # 一次写500个吧
            # 写容器可用IP
            for ipnums in more_itertools.chunked(xrange(base+gateway_count, base+network.size), 500):
                rds.sadd(n.storekey, *ipnums)

            # 写宿主机可用IP
            rds.sadd(n.gatekey, *range(base, base+gateway_count))
            return n
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def list_networks(cls, start=0, limit=20):
        q = cls.query.order_by(cls.id.asc()).offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_by_netspace(cls, netspace):
        return cls.query.filter_by(netspace=netspace).first()

    @property
    def storekey(self):
        return 'eru:network:%s:ips' % self.name

    @property
    def gatekey(self):
        return 'eru:network:%s:hosts' % self.name

    @property
    def hostmask_string(self):
        return self.netspace.split('/')[-1]

    @property
    def network(self):
        return IPNetwork(self.netspace)

    @property
    def pool_size(self):
        return rds.scard(self.storekey)

    @property
    def gate_pool_size(self):
        return rds.scard(self.gatekey)

    @property
    def used_count(self):
        return (self.network.size - self.gateway_count) - self.pool_size

    @property
    def used_gate_count(self):
        return self.gateway_count - self.gate_pool_size

    def __contains__(self, ip):
        return self.contains_ip(ip)

    @redis_lock('net:acquire_ip:{self.id}')
    def contains_ip(self, ip):
        """ip is unicode or IPAddress object"""
        if isinstance(ip, basestring):
            try:
                ip = IPAddress(ip)
            except AddrFormatError:
                return False
        return rds.sismember(self.storekey, ip.value)

    @redis_lock('net:acquire_ip:{self.id}')
    def acquire_ip(self):
        """take an IP from network, return an IP object"""
        ipnum = rds.spop(self.storekey)
        return ipnum and IP.create(ipnum, self) or None

    @redis_lock('net:acquire_ip:{self.id}')
    def acquire_specific_ip(self, ip_str):
        """take a specific IP from network"""
        try:
            ip = IPAddress(ip_str)
        except ValueError:
            return None

        if rds.sismember(self.storekey, ip.value):
            rds.srem(self.storekey, ip.value)
            return IP.create(ip.value, self)

    @redis_lock('net:acquire_ip:{self.id}')
    def release_ip(self, ip):
        rds.sadd(self.storekey, int(ip))

    @redis_lock('net:gateway_ip:{self.id}')
    def acquire_gateway_ip(self, host):
        ipnum = rds.spop(self.gatekey)
        if not ipnum:
            return

        vg = VLanGateway.create(ipnum, self.id, host.id)
        if not vg:
            rds.sadd(self.gatekey, ipnum)
            return

        return vg

    @redis_lock('net:gateway_ip:{self.id}')
    def release_gateway(self, ip):
        rds.sadd(self.gatekey, int(ip))

    def add_ip(self, ip):
        if isinstance(ip, basestring):
            try:
                ip = IPAddress(ip)
            except AddrFormatError:
                return False
        ipnum = ip.value
        if rds.sismember(self.gatekey, ipnum):
            rds.srem(self.gatekey, ipnum)
        rds.sadd(self.storekey, ipnum)
        return True

    def to_dict(self):
        d = super(Network, self).to_dict()
        d.update(
            pool_size=self.pool_size,
            used_count=self.used_count,
        )
        return d
