# coding: utf-8

from flask import Blueprint, g, current_app, request

from eru import consts
from eru.models import Host
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException
from eru.helpers.docker import save_docker_certs

bp = Blueprint('host', __name__, url_prefix='/api/host')

def _get_host(id_or_name):
    if id_or_name.isdigit():
        return Host.get(id_or_name)
    return Host.get_by_name(id_or_name)

@bp.route('/<id_or_name>/', methods=['GET'])
@jsonify
def get_host(id_or_name):
    host = _get_host(id_or_name)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % id_or_name)
    return host

@bp.route('/<id_or_name>/certs/', methods=['PUT'])
@jsonify
def put_host_certs(id_or_name):
    host = _get_host(id_or_name)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % id_or_name)
    ca, cert, key = request.files['ca'], request.files['cert'], request.files['key']
    try:
        save_docker_certs(host, ca.read(), cert.read(), key.read())
    finally:
        ca.close()
        cert.close()
        key.close()
    return {'r': 0, 'msg': 'OK'}

@bp.route('/<id_or_name>/down/', methods=['PUT', 'POST'])
@jsonify
def kill_host(id_or_name):
    host = _get_host(id_or_name)
    if host:
        host.kill()
        current_app.logger.info('Kill host (hostname=%s)', id_or_name)
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<id_or_name>/cure/', methods=['PUT', 'POST'])
@jsonify
def cure_host(id_or_name):
    host = _get_host(id_or_name)
    if host:
        host.cure()
        current_app.logger.info('Cure host (hostname=%s)', id_or_name)
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<id_or_name>/containers/', methods=['GET'])
@jsonify
def list_host_containers(id_or_name):
    host = _get_host(id_or_name)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % id_or_name)
    containers = host.list_containers(g.start, g.limit)
    return {'r': 0, 'msg': consts.OK, 'containers': containers}
