# coding: utf-8

from flask import Blueprint

from eru.models import Host
from eru.common import code
from eru.utils.views import jsonify, EruAbortException

bp = Blueprint('host', __name__, url_prefix='/api/host')

@bp.route('/<int:host_id>/', methods=['GET'])
@jsonify()
def get_network(host_id):
    host = Host.get(host_id)
    if not host:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Host %s not found' % host_id)
    return host

@bp.route('/<string:host_name>/', methods=['GET'])
@jsonify()
def get_network_by_name(host_name):
    host = Host.get_by_name(host_name)
    if not host:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Host %s not found' % host_name)
    return host

@bp.route('/<string:host_name>/kill/', methods=['PUT', 'POST'])
@jsonify()
def kill_host(host_name):
    host = Host.get_by_name(host_name)
    if host:
        host.kill()
    return {'r': 0, 'msg': code.OK}

@bp.route('/<string:host_name>/cure/', methods=['PUT', 'POST'])
@jsonify()
def cure_host(host_name):
    host = Host.get_by_name(host_name)
    if host:
        host.cure()
    return {'r': 0, 'msg': code.OK}

@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}
