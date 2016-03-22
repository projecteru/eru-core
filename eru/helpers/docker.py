import logging
import os

from eru.config import DOCKER_CERT_PATH
from eru.connection import rds
from eru.utils.ensure import ensure_file, ensure_dir


_log = logging.getLogger(__name__)
needed_cert_files = ('ca.pem', 'cert.pem', 'key.pem')


def save_docker_certs(ip, *certs):
    """
    save certs in DOCKER_CERT_PATH/{ip} as well as redis
    :param ip: str, host ip address
    :param certs: tuple of str, content of .pem files, must be (ca, cert, key)
    """
    if not DOCKER_CERT_PATH:
        _log.warn('DOCKER_CERT_PATH not set')
        return

    certs_dir = make_certs_dir(ip)
    for fname, content in zip(needed_cert_files, certs):
        key = make_redis_cert_file_key(ip, fname)
        rds.set(key, content)
        ensure_file(os.path.join(certs_dir, fname), mode=0444, content=content)


def get_docker_certs(ip):
    """
    return valid .cert absolute file paths: (ca_path, cert_path, key_path), in
    the mean time, ensure the files are on both local and redis
    """
    results = []
    # make sure the directory for the cert files is created
    make_certs_dir(ip)
    for fname in needed_cert_files:
        file_path = make_cert_path(ip, fname)
        key = make_redis_cert_file_key(ip, fname)

        # respect redis file first, if not found, provide with local copy,
        # this could make things easier when changing certificate files
        content = rds.get(key)
        if content:
            ensure_file(file_path, mode=0444, content=content)
        else:
            with open(file_path) as f:
                rds.set(key, f.read())

        results.append(file_path)

    return results


def make_cert_path(ip, file_name):
    """
    make up the local path for the given .pem file according to DOCKER_CERT_PATH
    :param ip: str, {ip}:{port}, could be a single ip as well
    :param file_name: str, choose from ['ca.pem', 'cert.pem', 'key.pem']
    """
    ip = ip.split(':', 1)[0]
    cert_folder = os.path.join(DOCKER_CERT_PATH, ip)
    path = os.path.join(cert_folder, file_name)
    return path


def make_redis_cert_file_key(ip, file_name):
    return 'docker:certfile:{}:{}'.format(ip, file_name)


def make_certs_dir(ip):
    certs_dir = os.path.join(DOCKER_CERT_PATH, ip)
    ensure_dir(certs_dir)
    return certs_dir
