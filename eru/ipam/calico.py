# coding: utf-8

import os
from netaddr import IPAddress, IPNetwork, AddrFormatError
from pycalico.ipam import IPAMClient
from pycalico.datastore import ETCD_SCHEME_ENV, ETCD_AUTHORITY_ENV
from pycalico.datastore_datatypes import IPPool

from eru.agent import get_agent
from eru.config import ETCD
from eru.ipam.base import BaseIPAM
from eru.ipam.structure import WrappedIP, WrappedNetwork


def _get_client():
    os.environ[ETCD_SCHEME_ENV] = 'http'
    os.environ[ETCD_AUTHORITY_ENV] = ETCD
    return IPAMClient()


_ipam = _get_client()


def _get_container_ips(container_id):
    from eru.models.container import Container

    container = Container.get_by_container_id(container_id)
    hostname = container.host.name
    endpoints = _ipam.get_endpoints(hostname=hostname,
            orchestrator_id='docker',
            workload_id=container.container_id)

    return [IPAddress(i) for endpoint in endpoints for i in endpoint.ipv4_nets]


class CalicoIPAM(BaseIPAM):
    """
    IPAM use calico. We do Network create/delete, we do IP release,
    but we don't do IP assignment, assignment is done by agent with calicoctl.
    """

    def add_ip_pool(self, cidr, name):
        try:
            pool = IPPool(cidr, masquerade=True, ipam=True)
        except AddrFormatError:
            return

        _ipam.add_ip_pool(4, pool)
        return WrappedNetwork.from_calico(pool)

    def remove_ip_pool(self, cidr):
        try:
            cidr = IPNetwork(cidr)
        except AddrFormatError:
            return

        _ipam.remove_ip_pool(4, cidr)

    def get_pool(self, cidr):
        try:
            cidr = IPNetwork(cidr)
        except AddrFormatError:
            return

        pool = _ipam.get_pool(IPAddress(cidr.first))
        return WrappedNetwork.from_calico(pool)

    def get_all_pools(self):
        pools = _ipam.get_ip_pools(4)
        return [WrappedNetwork.from_calico(p) for p in pools]

    def allocate_ips(self, cidrs, container_id, spec_ips=None):
        """
        Allocate IPs for container_id, all done by calicoctl.
        If spec_ips is given, cidrs will be ignored.
        Note: agent use calicoctl to assign IPs and it will do all the things related to calico,
            so here we only need to tell agent which ip to assign.
        Generally we give cidr to agent, and maybe IPs instead.
        """
        from eru.models.container import Container

        def _release_ips(ips):
            ips = set([IPAddress(i) for i in ips])
            _ipam.release_ips(set(ips))

        container = Container.get_by_container_id(container_id)
        agent = get_agent(container.host)
        ip_list = spec_ips or cidrs

        resp = agent.add_contianer_calico(container_id, ip_list)
        if resp.status_code != 200:
            _release_ips(ip_list)
            return False

        rv = resp.json()
        if not all(r['succ'] for r in rv):
            _release_ips(ip_list)
            return False

        return True

    def reallocate_ips(self, container_id):
        """
        Refresh IPs on container_id, need to release them first,
        otherwise agent is unable to assign them again.
        """
        ip_list = _get_container_ips(container_id)
        ip_list = [str(i) for i in ip_list]

        self.release_ip_by_container(container_id)
        return self.allocate_ips(None, container_id, ip_list)

    def get_ip_by_container(self, container_id):
        """Copied from calicoctl, must use endpoint to get IPs bound to container_id"""
        ip_list = _get_container_ips(container_id)
        pools = [_ipam.get_pool(ip) for ip in ip_list]
        return [WrappedIP.from_calico(ip, pool, container_id) for ip, pool in zip(ip_list, pools)]

    def release_ip_by_container(self, container_id):
        """We don't use IPv6 addresses. Copied from calicoctl."""
        from eru.models.container import Container
        container = Container.get_by_container_id(container_id)
        hostname = container.host.name

        endpoints = _ipam.get_endpoints(hostname=hostname,
                orchestrator_id='docker',
                workload_id=container.container_id)

        for endpoint in endpoints:
            ip_set = set([IPAddress(i) for i in endpoint.ipv4_nets])
            _ipam.release_ip(ip_set)
            _ipam.remove_endpoint(endpoint)

        try:
            _ipam.remove_workload(hostname, 'docker', container.container_id)
        except KeyError:
            pass
