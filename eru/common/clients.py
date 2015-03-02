# coding: utf-8

import etcd
import docker
import redis

from eru.common import settings
from eru.storage.redis import RedisStorage
from eru.storage.etcd import EtcdStorage


def get_docker_client(addr):
    base_url = 'tcp://%s' % addr
    return docker.Client(base_url=base_url)


def get_etcd_client(addr):
    if isinstance(addr, tuple):
        return etcd.Client(host=addr)
    elif isinstance(addr, basestring):
        host, port = addr.split(':')
        return etcd.Client(host, int(port))
    raise ValueError('etcd addr must be tuple or string')


def get_redis_client(host, port , max_connections):
    pool = redis.ConnectionPool(host=host, port=port, max_connections=max_connections)
    return redis.Redis(connection_pool=pool)


rds = get_redis_client(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_POOL_SIZE)


if settings.ERU_CONFIG_BACKEND == 'redis':
    config_backend = RedisStorage(rds)
elif settings.ERU_CONFIG_BACKEND == 'etcd':
    config_backend = EtcdStorage(get_etcd_client(settings.ETCD_MACHINES))
else:
    raise RuntimeError('ERU_CONFIG_BACKEND must be redis/etcd')

