# coding: utf-8

from flask import abort, g, current_app, request

from eru import consts
from eru.models import Host, Network, VLanGateway
from eru.helpers.docker import save_docker_certs

from .bp import create_api_blueprint


bp = create_api_blueprint('host', __name__, url_prefix='/api/host')


def _get_host(id_or_name):
    if id_or_name.isdigit():
        host = Host.get(id_or_name)
    else:
        host = Host.get_by_name(id_or_name)
    if not host:
        abort(404, 'Host %s not found' % id_or_name)
    return host


@bp.route('/<id_or_name>/', methods=['GET'])
def get_host(id_or_name):
    return _get_host(id_or_name)


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
    return {'r': 0, 'msg': 'OK'}


@bp.route('/<id_or_name>/down/', methods=['PUT', 'POST'])
def kill_host(id_or_name):
    host = _get_host(id_or_name)
    host.kill()
    current_app.logger.info('Kill host (hostname=%s)', id_or_name)
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<id_or_name>/cure/', methods=['PUT', 'POST'])
def cure_host(id_or_name):
    host = _get_host(id_or_name)
    host.cure()
    current_app.logger.info('Cure host (hostname=%s)', id_or_name)
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<id_or_name>/containers/', methods=['GET'])
def list_host_containers(id_or_name):
    host = _get_host(id_or_name)
    containers = host.list_containers(g.start, g.limit)
    return {'r': 0, 'msg': consts.OK, 'containers': containers}


@bp.route('/<id_or_name>/macvlan/', methods=['POST', 'GET', 'DELETE'])
def macvlan(id_or_name):
    host = _get_host(id_or_name)
    if request.method == 'GET':
        return host.list_vlans(g.start, g.limit)

    data = request.get_json()
    netname = data.get('network', '')
    network = Network.get_by_name(netname)
    if not network:
        abort(404, 'Network not found')

    if request.method == 'POST':
        return network.acquire_gateway_ip(host)
    elif request.method == 'DELETE':
        vg = VLanGateway.get_by_host_and_network(host.id, network.id)
        if vg:
            vg.release()
        return {'r': 0, 'msg': consts.OK}
