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
        ips = [{'nid': n, 'ip': ip} for (n, ip) in ip_list]
        payload = {
            'task_id': task_id,
            'ips': ips,
        }
        return self._request('POST', url, payload)
