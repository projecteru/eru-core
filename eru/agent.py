# coding: utf-8

import json
import requests
from eru.config import ERU_AGENT_PORT

_agent_clients = {}


def get_agent(host):
    agent = _agent_clients.get(host.ip, None)
    if agent:
        return agent
    agent = Agent(host.ip, ERU_AGENT_PORT)
    _agent_clients[host.ip] = agent
    return agent


class Agent(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.session = requests.Session()
        self.base_url = 'http://%s:%s' % (host.replace('http://', ''), port)

    def _request(self, method, url, payload):
        headers = {'content-type': 'application/json'}
        data = json.dumps(payload)
        target_url = self.base_url + url
        return self.session.request(method=method, url=target_url,
                data=data, headers=headers)

    def add_container(self, container):
        url = '/api/container/add/'
        payload = {
            'control': '+',
            'container_id': container.container_id,
            'meta': container.meta,
        }
        return self._request('POST', url, payload)

    def add_container_vlan(self, container_id, task_id, ip_list):
        url = '/api/container/%s/addvlan/' % container_id
        payload = [{'nid': n, 'ip': ip} for (n, ip) in ip_list]
        return self._request('POST', url, payload)

    def set_default_route(self, container_id, ip):
        url = '/api/container/%s/setroute/' % container_id
        payload = {'ip': ip}
        return self._request('POST', url, payload)

    def add_container_calico(self, container_id, ip_list):
        url = '/api/container/%s/addcalico/' % container_id
        payload = [{'nid': n, 'ip': ip, 'profile': profile, 'append': append} for (n, ip, profile, append) in ip_list]
        return self._request('POST', url, payload)

    def _publish_container(self, url, eip, container):
        backends = container.get_backends()
        if not backends:
            return

        payload = {'eip': str(eip), 'protocol': 'tcp'}
        for backend in backends:
            _, port = backend.split(':', 1)
            payload['port'] = port
            payload['dest'] = backend
            payload['ident'] = '%s_%s' % (container.name, port)
            self._request('POST', url, payload)

        # we don't care the return value
        # just ignore this...

    def publish_container(self, eip, container):
        url = '/api/container/publish/'
        return self._publish_container(url, eip, container)

    def unpublish_container(self, eip, container):
        url = '/api/container/disable/'
        return self._publish_container(url, eip, container)

    def bind_eip(self, ip_list):
        url = '/api/eip/bind/'
        payload = [{'ip': ip, 'id': id, 'broadcast': b} for ip, id, b in ip_list]
        return self._request('POST', url, payload)

    def unbind_eip(self, ip_list):
        url = '/api/eip/release/'
        payload = [{'ip': ip, 'id': id} for ip, id in ip_list]
        return self._request('POST', url, payload)
