# coding: utf-8

import os
import redis
import docker
from docker.tls import TLSConfig

from eru.config import (
    DOCKER_CERT_PATH,
    DOCKER_REGISTRY_URL,
    DOCKER_REGISTRY_EMAIL,
    DOCKER_REGISTRY_USERNAME,
    DOCKER_REGISTRY_PASSWORD,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_POOL_SIZE,
)
from eru.storage.redis import RedisStorage

_docker_clients = {}

def get_docker_client(addr):
    """
    如果设置了 DOCKER_CERT_PATH, 那么证书需要位于 $DOCKER_CERT_PATH/${ip} 目录下.
    没有设置 DOCKER_CERT_PATH, 那么就简单连接就可以了.
    """
    client = _docker_clients.get(addr, None)
    if client:
        return client

    host = 'tcp://%s' % addr
    tls = None

    if DOCKER_CERT_PATH:
        cert_path = os.path.join(DOCKER_CERT_PATH, addr.split(':', 1)[0])
        host = 'https://%s' % addr
        tls = TLSConfig(
            client_cert=(
                os.path.join(cert_path, 'cert.pem'),
                os.path.join(cert_path, 'key.pem')
            ),
            ca_cert=os.path.join(cert_path, 'ca.pem'),
            verify=True,
            ssl_version=None,
            assert_hostname=False,
        )
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

def get_redis_client(host, port , max_connections):
    pool = redis.ConnectionPool(host=host, port=port, max_connections=max_connections)
    return redis.Redis(connection_pool=pool)

rds = get_redis_client(REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE)
config_backend = RedisStorage(rds)
