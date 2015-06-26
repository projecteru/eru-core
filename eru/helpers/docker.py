import os

from eru.utils.ensure import ensure_file, ensure_dir
from eru.config import DOCKER_CERT_PATH

def save_docker_certs(host_or_ip, ca, cert, key):
    if not DOCKER_CERT_PATH:
        return
    if not isinstance(host_or_ip, basestring):
        host_or_ip = host_or_ip.ip
    base_dir = os.path.join(DOCKER_CERT_PATH, host_or_ip)
    ensure_dir(base_dir)
    ensure_file(os.path.join(base_dir, 'ca.pem'), mode=0444, content=ca)
    ensure_file(os.path.join(base_dir, 'cert.pem'), mode=0444, content=cert)
    ensure_file(os.path.join(base_dir, 'key.pem'), mode=0400, content=key)
