# coding: utf-8

import os
import redis
import docker
from docker.utils import kwargs_from_env

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

def get_docker_client(addr):
    """
    如果设置了 DOCKER_CERT_PATH, 那么证书需要位于 $DOCKER_CERT_PATH/${ip} 目录下.
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

def get_redis_client(host, port , max_connections):
    pool = redis.ConnectionPool(host=host, port=port, max_connections=max_connections)
    return redis.Redis(connection_pool=pool)

rds = get_redis_client(REDIS_HOST, REDIS_PORT, REDIS_POOL_SIZE)
config_backend = RedisStorage(rds)
