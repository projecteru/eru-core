# coding: utf-8

"""Some structures used outside ipam as return value."""

from eru.models.base import Jsonized


class WrappedIP(Jsonized):

    def __init__(self, id, ipnum, vethname, network_id, container_id,
            address, vlan_address, raw):
        self.id = id
        self.ipnum = ipnum
        self.vethname = vethname
        self.network_id = network_id
        self.container_id = container_id
        self.address = address
        self.vlan_address = vlan_address
        self._raw = raw

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def __str__(self):
        return str(self._raw)

    def __int__(self):
        return int(self._raw)

    @classmethod
    def from_macvlan(cls, ip):
        return cls(ip.id, ip.ipnum, ip.vethname, ip.network_id,
                ip.container_id, ip.address, ip.vlan_address, ip)

    @classmethod
    def from_calico(cls, ip):
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'ipnum': self.ipnum,
            'vethname': self.vethname,
            'network_id': self.network_id,
            'container_id': self.container_id,
            'address': self.address,
            'vlan_address': self.vlan_address,
        }


class WrappedNetwork(Jsonized):

    def __init__(self, id, name, netspace, cidr,
            gateway_count, pool_size, used_count, raw):
        self.id = id
        self.name = name
        self.netspace = netspace
        self.cidr = cidr
        self.gateway_count = gateway_count
        self.pool_size = pool_size
        self.used_count = used_count
        self._raw = raw

    def __contains__(self, ip):
        return ip in self._raw

    def __getattr__(self, name):
        return getattr(self._raw, name)

    @classmethod
    def from_macvlan(cls, network):
        return cls(network.id, network.name, network.netspace, network.netspace,
                network.gateway_count, network.pool_size, network.used_count,
                network)

    @classmethod
    def from_calico(cls, network):
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'netspace': self.netspace,
            'cidr': self.cidr,
            'gateway_count': self.gateway_count,
            'pool_size': self.pool_size,
            'used_count': self.used_count,
        }
