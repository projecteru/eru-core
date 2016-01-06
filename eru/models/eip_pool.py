# coding: utf-8

from netaddr import IPAddress
from eru.clients import rds


class EIPPool(object):

    EIP_POOL_KEY = 'eru:eip:pool' 

    def add_eip(self, *eips):
        rds.sadd(self.EIP_POOL_KEY, *[eip.value for eip in eips])

    def get_eip(self, eip=None):
        if eip is None:
            value = rds.spop(self.EIP_POOL_KEY)
            return value and IPAddress(value) or None

        value = rds.srem(self.EIP_POOL_KEY, eip.value)
        return value and eip or None

    def __len__(self):
        return rds.scard(self.EIP_POOL_KEY)

    def __str__(self):
        return '<EIPPool with %s IPs available>' % len(self)


eip_pool = EIPPool()
