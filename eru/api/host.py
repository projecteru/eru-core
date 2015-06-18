# coding: utf-8

from flask import Blueprint, g, current_app

from eru import consts
from eru.models import Host
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException

bp = Blueprint('host', __name__, url_prefix='/api/host')

@bp.route('/<int:host_id>/', methods=['GET'])
@jsonify
def get_host(host_id):
    host = Host.get(host_id)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % host_id)
    return host

@bp.route('/<string:host_name>/', methods=['GET'])
@jsonify
def get_host_by_name(host_name):
    host = Host.get_by_name(host_name)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % host_name)
    return host

@bp.route('/<string:host_name>/down/', methods=['PUT', 'POST'])
@jsonify
def kill_host(host_name):
    host = Host.get_by_name(host_name)
    if host:
        host.kill()
        current_app.logger.info('Kill host (hostname=%s)', host_name)
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<string:host_name>/cure/', methods=['PUT', 'POST'])
@jsonify
def cure_host(host_name):
    host = Host.get_by_name(host_name)
    if host:
        host.cure()
        current_app.logger.info('Cure host (hostname=%s)', host_name)
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<string:host_name>/containers/', methods=['GET'])
@jsonify
def list_host_containers(host_name):
    host = Host.get_by_name(host_name)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % host_name)
    containers = host.list_containers(g.start, g.limit)
    return {'r': 0, 'msg': consts.OK, 'containers': containers}
