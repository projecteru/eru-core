import os

from eru.utils.ensure import ensure_file
from eru.config import DOCKER_CERT_PATH

def save_docker_certs(host, ca, cert, key):
    if not DOCKER_CERT_PATH:
        return
    base_dir = os.path.join(DOCKER_CERT_PATH, host.ip)
    ensure_file(os.path.join(base_dir, 'ca.pem'), mode=0400, content=ca)
    ensure_file(os.path.join(base_dir, 'cert.pem'), mode=0400, content=cert)
    ensure_file(os.path.join(base_dir, 'key.pem'), mode=0400, content=key)
