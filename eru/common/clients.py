# coding: utf-8

import types
import etcd
import docker
import redis
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

def get_redis_client():
    pool = redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        max_connections=settings.REDIS_POOL_SIZE,
    )
    return redis.Redis(connection_pool=pool)

etcd_client = get_etcd_client(settings.ETCD_MACHINES)
rdb = get_redis_client()

