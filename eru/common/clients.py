# coding: utf-8

import types
import etcd
import docker
from eru.common import settings


def get_docker_client(addr):
    base_url = 'tcp://%s' % addr
    return docker.Client(base_url=base_url)


def get_etcd_client(addr):
    if isinstance(addr, tuple):
        return etcd.Client(host=addr)
    elif isinstance(addr, types.StringTypes):
        host, port = addr.split(':')
        return etcd.Client(host, int(port))
    raise ValueError('etcd addr must be tuple or string')
    

etcd_client = get_etcd_client(settings.ETCD_MACHINES)

