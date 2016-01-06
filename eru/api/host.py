# coding: utf-8

import logging
from flask import abort, g, request

from eru.ipam import ipam
from eru.models import Pod, Host, VLanGateway
from eru.clients import get_docker_client
from eru.helpers.docker import save_docker_certs

from .bp import create_api_blueprint, DEFAULT_RETURN_VALUE

bp = create_api_blueprint('host', __name__, url_prefix='/api/host')
_log = logging.getLogger(__name__)


def _get_host(id_or_name):
    host = Host.get(id_or_name) or Host.get_by_name(id_or_name)
    if not host:
        abort(404, 'Host %s not found' % id_or_name)
    return host


@bp.route('/<id_or_name>/', methods=['GET'])
def get_host(id_or_name):
    return _get_host(id_or_name)


@bp.route('/create/', methods=['POST'])
def create_host():
    """为了文件, 只好不用json了"""
    addr = request.form.get('addr', default='')
    podname = request.form.get('podname', default='')
    if not (addr and podname):
        abort(400, 'Need addr and podname')

    pod = Pod.get_by_name(podname)
    if not pod:
        abort(400, 'No pod found')

    # 存证书, 没有就算了
    if all(k in request.files for k in ['ca', 'cert', 'key']):
        try:
            ca, cert, key = request.files['ca'], request.files['cert'], request.files['key']
            save_docker_certs(addr.split(':', 1)[0], ca.read(), cert.read(), key.read())
        finally:
            ca.close()
            cert.close()
            key.close()

    try:
        client = get_docker_client(addr, force_flush=True)
        info = client.info()
    except Exception as e:
        abort(400, 'Docker daemon error on host %s, error: %s' % (addr, e.message))

    if not Host.create(pod, addr, info['Name'], info['ID'], info['NCPU'], info['MemTotal']):
        abort(400, 'Error while creating host')
    return 201, DEFAULT_RETURN_VALUE


@bp.route('/<id_or_name>/certs/', methods=['PUT'])
def put_host_certs(id_or_name):
    host = _get_host(id_or_name)
    ca, cert, key = request.files['ca'], request.files['cert'], request.files['key']
    try:
        save_docker_certs(host, ca.read(), cert.read(), key.read())
    finally:
        ca.close()
        cert.close()
        key.close()
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_name>/macvlan/', methods=['POST', 'GET', 'DELETE'])
def macvlan(id_or_name):
    host = _get_host(id_or_name)
    if request.method == 'GET':
        return host.list_vlans(g.start, g.limit)

    data = request.get_json()
    netname = data.get('network', '')
    network = ipam.get_pool(netname)
    if not network:
        abort(404, 'Network not found')

    vg = VLanGateway.get_by_host_and_network(host.id, network.id)
    if request.method == 'POST':
        return vg or network.acquire_gateway_ip(host)
    elif request.method == 'DELETE':
        if vg:
            vg.release()
        return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_name>/containers/', methods=['GET'])
def list_host_containers(id_or_name):
    host = _get_host(id_or_name)
    return host.list_containers(g.start, g.limit)


@bp.route('/<id_or_name>/eip/', methods=['POST', 'DELETE', 'GET'])
def bind_eip(id_or_name):
    host = _get_host(id_or_name)
    if request.method == 'POST':
        return {'eip': str(host.bind_eip())}
    elif request.method == 'GET':
        return [str(eip) for eip in host.eips]

    host.release_eip()
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_name>/<method>/', methods=['PUT'])
def set_status(id_or_name, method):
    if method not in ('public', 'private', 'cure', 'down', 'kill'):
        abort(400, 'Not found')

    _methods = {
        'public': 'set_public',
        'private': 'set_private',
        'down': 'kill',
    }
    method = _methods.get(method, method)
    host = _get_host(id_or_name)
    getattr(host, method)()

    _log.info('Host (hostname=%s) %s', id_or_name, method)
    return DEFAULT_RETURN_VALUE
