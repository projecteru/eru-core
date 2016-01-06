# coding: utf-8

import os
from netaddr import IPAddress, IPNetwork, AddrFormatError
from pycalico.ipam import IPAMClient
from pycalico.datastore import ETCD_SCHEME_ENV, ETCD_AUTHORITY_ENV
from pycalico.datastore_datatypes import IPPool

from eru.agent import get_agent
from eru.clients import rds
from eru.config import ETCD
from eru.ipam.base import BaseIPAM
from eru.ipam.structure import WrappedIP, WrappedNetwork
from eru.models.eip_pool import eip_pool


def _get_client():
    os.environ[ETCD_SCHEME_ENV] = 'http'
    os.environ[ETCD_AUTHORITY_ENV] = ETCD
    return IPAMClient()


_ipam = _get_client()
_POOL_NAME_KEY = 'eru:ipam:calico:%s:pool'
_POOL_CIDR_KEY = 'eru:ipam:calico:%s:cidr'


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
        except (AddrFormatError, ValueError):
            return

        _ipam.add_ip_pool(4, pool)
        _ipam.create_profile(name)
        rds.set(_POOL_NAME_KEY % pool.cidr, name)
        rds.set(_POOL_CIDR_KEY % name, pool.cidr)
        return WrappedNetwork.from_calico(pool, name)

    def remove_ip_pool(self, cidr):
        try:
            cidr = IPNetwork(cidr)
        except (AddrFormatError, ValueError):
            return

        name = rds.get(_POOL_NAME_KEY % cidr)
        rds.delete(_POOL_NAME_KEY % cidr)
        rds.delete(_POOL_CIDR_KEY % name)
        _ipam.remove_ip_pool(4, cidr)
        _ipam.remove_profile(name)

    def get_pool(self, ip):
        """ip can be either an IP or a CIDR"""
        if '/' in ip:
            try:
                ip = IPAddress(IPNetwork(ip).first)
            except (AddrFormatError, ValueError):
                return
        else:
            try:
                ip = IPAddress(ip)
            except (AddrFormatError, ValueError):
                return

        pool = _ipam.get_pool(ip)
        name = rds.get(_POOL_NAME_KEY % pool.cidr)
        return WrappedNetwork.from_calico(pool, name)

    def get_all_pools(self):
        pools = _ipam.get_ip_pools(4)
        names = [rds.get(_POOL_NAME_KEY % p.cidr) for p in pools]
        return [WrappedNetwork.from_calico(p, name) for p, name in zip(pools, names)]

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
            try:
                ips = set([IPAddress(i) for i in ips])
            except (AddrFormatError, ValueError):
                return
            _ipam.release_ips(set(ips))

        ip_list = spec_ips or cidrs
        if not ip_list:
            return True

        container = Container.get_by_container_id(container_id)
        agent = get_agent(container.host)

        pools = [self.get_pool(ip) for ip in ip_list]
        profiles = [p.name for p in pools]

        count = len(_get_container_ips(container.container_id))
        nstart = count+1 if count > 0 else 0
        nids = range(nstart, nstart+len(ip_list))
        appends = [True for _ in nids]
        if count == 0:
            appends[0] = False

        resp = agent.add_container_calico(container_id, zip(nids, ip_list, profiles, appends))
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
            _ipam.release_ips(ip_set)
            _ipam.remove_endpoint(endpoint)

        try:
            _ipam.remove_workload(hostname, 'docker', container.container_id)
        except KeyError:
            pass

    def add_eip(self, *eips):
        eips = [IPAddress(eip) for eip in eips]
        eip_pool.add_eip(*eips)

    def get_eip(self, eip=None):
        eip = eip and IPAddress(eip) or None
        return eip_pool.get_eip(eip)
