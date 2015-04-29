# coding: utf-8

import more_itertools
import sqlalchemy.exc
from ipaddress import IPv4Network, IPv4Address

from eru.common.clients import rds
from eru.models import db
from eru.models.base import Base

class IP(Base):

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
        try:
            ip = cls(ipnum, network)
            db.session.add(ip)
            db.session.commit()
            return ip
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @property
    def address(self):
        return str(IPv4Address(self.ipnum))

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

    def __str__(self):
        return self.address

    def __int__(self):
        return self.ipnum

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

class Network(Base):

    __tablename__ = 'network'

    name = db.Column(db.CHAR(40), unique=True, nullable=False)
    netspace = db.Column(db.CHAR(40), nullable=False, default='')

    ips = db.relationship('IP', backref='network', lazy='dynamic')

    def __init__(self, name, netspace):
        self.name = name
        self.netspace = netspace

    @classmethod
    def create(cls, name, netspace):
        """create network and store ips(int) under this network in redis"""
        try:
            n = cls(name, netspace)
            db.session.add(n)
            db.session.commit()

            # create sub IPs
            network = n.network
            base = int(network.network_address)
            # 一次写500个吧
            for ipnums in more_itertools.chunked(xrange(base+1, base+network.num_addresses), 500):
                rds.sadd(n.storekey, *ipnums)

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

    @property
    def storekey(self):
        return 'eru:network:%s:ips' % self.name

    @property
    def hostmask_string(self):
        return self.netspace.split('/')[-1]

    @property
    def network(self):
        return IPv4Network(unicode(self.netspace))

    @property
    def pool_size(self):
        return rds.scard(self.storekey)

    @property
    def used_count(self):
        # 网关就不要给别人了
        n = self.network
        return (n.num_addresses - 1) - self.pool_size

    def acquire_ip(self):
        """take an IP from network, return an IP object"""
        ipnum = rds.spop(self.storekey)
        return ipnum and IP.create(ipnum, self) or None

    def release_ip(self, ip):
        """return this IP, which is an IP object"""
        rds.sadd(self.storekey, int(ip))

    def to_dict(self):
        d = super(Network, self).to_dict()
        d.update(
            pool_size=self.pool_size,
            used_count=self.used_count,
        )
        return d
