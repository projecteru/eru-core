# coding: utf-8
import os

import docker
from docker.tls import TLSConfig

from eru.config import (
    DOCKER_CERT_PATH,
    DOCKER_REGISTRY_URL,
    DOCKER_REGISTRY_EMAIL,
    DOCKER_REGISTRY_USERNAME,
    DOCKER_REGISTRY_PASSWORD,
)


_docker_clients = {}

def get_docker_client(addr, force_flush=False):
    """
    如果设置了 DOCKER_CERT_PATH, 那么证书需要位于 $DOCKER_CERT_PATH/${ip} 目录下.
    没有设置 DOCKER_CERT_PATH, 那么就简单连接就可以了.
    """
    client = _docker_clients.get(addr, None)
    if client and not force_flush:
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
