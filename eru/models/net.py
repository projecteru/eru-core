# coding: utf-8

import sqlalchemy.exc
from ipaddress import IPv4Network, IPv4Address

from eru.common.clients import rds
from eru.models import db
from eru.models.base import Base

class Network(Base):

    __tablename__ = 'network'

    name = db.Column(db.CHAR(40), unique=True, nullable=False)
    netspace = db.Column(db.CHAR(40), nullable=False, default='')

    def __init__(self, name, netspace):
        self.name = name
        self.netspace = netspace
        self.storekey = 'eru:macvlan:%s:ips' % name

    @classmethod
    def create(cls, name, netspace):
        """create network and store ips(int) under this network in redis"""
        try:
            n = cls(name, netspace)
            db.session.add(n)
            db.session.commit()

            network = IPv4Network(netspace)
            base = int(network.network_address)
            # TODO 可以分块写, 节约点io
            for offset in xrange(network.num_addresses):
                rds.rpush(n.storekey, base+offset)
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    def occupy_one_ip(self):
        ipnum = rds.lpop(self.storekey)
        return str(IPv4Address(ipnum))

    def release_ip(self, ip):
        ipnum = int(IPv4Address(unicode(ip)))
        rds.rpush(self.storekey, ipnum)
