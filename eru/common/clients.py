# coding: utf-8

import os
import etcd
import docker
import redis
from docker.utils import kwargs_from_env

from eru.common.settings import (
    DOCKER_REGISTRY_USERNAME, DOCKER_REGISTRY_PASSWORD,
    DOCKER_REGISTRY_EMAIL, DOCKER_REGISTRY_URL, DOCKER_CERT_PATH,
    REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE,
    ERU_CONFIG_BACKEND, ETCD_MACHINES,
)
from eru.storage.redis import RedisStorage
from eru.storage.etcd import EtcdStorage


def get_docker_client(addr):
    """
    如果设置了 DOCKER_CERT_PATH, 那么证书需要位于 $DOCKER_CERT_PATH/${ip} 目录下.
    有 ca.pem, cert.pem, key.pem 三个文件, 权限需要正确的 400.
    没有设置 DOCKER_CERT_PATH, 那么就简单连接就可以了.
    """
    host = 'tcp://%s' % addr
    ip = addr.split(':', 1)[0]

    os.environ['DOCKER_HOST'] = host
    if DOCKER_CERT_PATH:
        os.environ['DOCKER_TLS_VERIFY'] = '1'
        os.environ['DOCKER_CERT_PATH'] = os.path.join(DOCKER_CERT_PATH, ip)

    client = docker.Client(**kwargs_from_env(assert_hostname=False))

    if DOCKER_REGISTRY_USERNAME:
        client.login(
            DOCKER_REGISTRY_USERNAME,
            password=DOCKER_REGISTRY_PASSWORD,
            email=DOCKER_REGISTRY_EMAIL,
            registry=DOCKER_REGISTRY_URL,
        )
    return client


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


rds = get_redis_client(REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE)


if ERU_CONFIG_BACKEND == 'redis':
    config_backend = RedisStorage(rds)
elif ERU_CONFIG_BACKEND == 'etcd':
    config_backend = EtcdStorage(get_etcd_client(ETCD_MACHINES))
else:
    raise RuntimeError('ERU_CONFIG_BACKEND must be redis/etcd')

