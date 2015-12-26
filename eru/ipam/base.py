# coding: utf-8

class BaseIPAM(object):

    def add_ip_pool(self, cidr, name):
        """create an IP pool with cidr"""

    def remove_ip_pool(self, cidr):
        """remove an IP pool with cidr"""

    def get_pool(self, cidr):
        """return pool with cidr"""

    def get_all_pools():
        """list all pools"""

    def allocate_ips(cidrs, container_id, spec_ips=None):
        """allocate ip for container_id with cidrs,
        can specify ips with spec_ips"""

    def reallocate_ips(self, container_id):
        """rebind ips back to container_id"""

    def get_ip_by_container(self, container_id):
        """get ip assigned to container_id"""

    def release_ip(self, address):
        """release an IP and return it to the pool"""

    def release_ip_by_container(self, container_id):
        """release all IPs with container_id"""
