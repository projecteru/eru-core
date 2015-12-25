# coding: utf-8

from werkzeug.security import gen_salt

from eru.agent import get_agent
from eru.ipam.base import BaseIPAM
from eru.models.network import IP, Network
from eru.models.container import Container


class MacVLANIPAM(BaseIPAM):

    def add_ip_pool(self, cidr, name):
        return Network.create(name, cidr)
    
    def remove_ip_pool(self, cidr):
        network = Network.get_by_netspace(cidr)
        if network:
            network.delete()

    def get_pool(self, cidr):
        """
        macvlan used to use name to identify.
        so here cidr may be a name string.
        and for compating, cidr can also be id.
        """
        if cidr.isdigit():
            return Network.get(cidr)
        return Network.get_by_name(cidr) or Network.get_by_netspace(cidr)

    def get_all_pools(self):
        return Network.list_networks()

    def allocate_ips(self, cidrs, container_id, spec_ips=None):

        def _release_ips(ips):
            for ip in ips:
                ip.release()

        container = Container.get_by_container_id(container_id)
        nid = max([ip.network_id for ip in container.ips.all()] + [-1]) + 1

        networks = [Network.get_by_netspace(cidr) for cidr in cidrs]
        networks = [n for n in networks if n]

        if spec_ips:
            ips = [n.acquire_specific_ip(ip) for n, ip in zip(networks, spec_ips)]
        else:
            ips = [n.acquire_ip() for n in networks]

        ips = [i for i in ips if i]
        ip_dict = {ip.vlan_address: ip for ip in ips}

        agent = get_agent(container.host)
        ip_list = [(nid or ip.vlan_seq_id, ip.vlan_address) for ip in ips]

        resp = agent.add_container_vlan(container_id, gen_salt(8), ip_list)
        if resp.status_code != 200:
            _release_ips(ips)
            return False

        rv = resp.json()
        if not all(r['succ'] for r in rv):
            _release_ips(ips)
            return False

        for r in rv:
            ip = ip_dict.get(r['ip'], None)
            if ip:
                ip.set_vethname(r['veth'])
                ip.assigned_to_container(container)
        return True

    def release_ip(self, address):
        ip = IP.get_by_value(address.value)
        if not ip:
            return

        ip.release()

    def release_ip_by_container(self, container_id):
        container = Container.get_by_container_id(container_id)
        if not container:
            return

        ips = IP.get_by_container(container.id)
        for ip in ips:
            ip.release()
