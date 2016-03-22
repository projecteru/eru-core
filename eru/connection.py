# coding: utf-8

import redis
import docker
from etcd import Client as EtcdClient
from docker.tls import TLSConfig

from eru.config import (
    ETCD, REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE,
    DOCKER_CERT_PATH, DOCKER_REGISTRY_URL, DOCKER_REGISTRY_EMAIL,
    DOCKER_REGISTRY_USERNAME, DOCKER_REGISTRY_PASSWORD,
)


def get_redis_client(host, port , max_connections):
    pool = redis.ConnectionPool(host=host, port=port, max_connections=max_connections)
    return redis.Redis(connection_pool=pool)


_docker_clients = {}


def get_docker_client(addr, force_flush=False):
    """
    如果设置了 DOCKER_CERT_PATH, 那么证书需要位于 $DOCKER_CERT_PATH/${ip} 目录下.
    没有设置 DOCKER_CERT_PATH, 那么就简单连接就可以了.
    """
    from eru.helpers.docker import get_docker_certs
    client = _docker_clients.get(addr, None)
    if client and not force_flush:
        return client

    if DOCKER_CERT_PATH:
        ip = addr.split(':', 1)[0]
        ca_path, cer_path, key_path = get_docker_certs(ip)
        host = 'https://%s' % addr
        tls = TLSConfig(
            client_cert=(cer_path, key_path),
            ca_cert=ca_path,
            verify=True,
            ssl_version=None,
            assert_hostname=False,
        )
    else:
        host = 'tcp://%s' % addr
        tls = None

    client = docker.Client(base_url=host, tls=tls)

    if DOCKER_REGISTRY_USERNAME:
        client.login(
            DOCKER_REGISTRY_USERNAME,
            password=DOCKER_REGISTRY_PASSWORD,
            email=DOCKER_REGISTRY_EMAIL,
            registry=DOCKER_REGISTRY_URL,
        )
    _docker_clients[addr] = client
    return client


def get_etcd_client(url):
    host, port = ETCD.split(':')
    return EtcdClient(host=host, port=int(port))


rds = get_redis_client(REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE)
etcd = get_etcd_client(ETCD)
