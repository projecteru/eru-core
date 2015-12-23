# coding: utf-8

from flask import abort, request, current_app
from netaddr import IPNetwork, AddrFormatError

from eru import consts
from eru.models import Network
from eru.utils.decorator import check_request_json

from .bp import create_api_blueprint


bp = create_api_blueprint('network', __name__, url_prefix='/api/network')


@bp.route('/create/', methods=['POST'])
@check_request_json(['name', 'netspace'])
def create_network():
    data = request.get_json()
    n = Network.create(data['name'], data['netspace'])
    if not n:
        current_app.logger.info('Network create failed (name=%s, net=%s)',
                data['name'], data['netspace'])
        abort(400, 'Network create failed')
    current_app.logger.info('Network create succeeded (name=%s, net=%s)',
            data['name'], data['netspace'])
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<id_or_name>/', methods=['GET'])
def get_network(id_or_name):
    if id_or_name.isdigit():
        n = Network.get(id_or_name)
    else:
        n = Network.get_by_name(id_or_name)
    if not n:
        abort(404, 'Network %s not found' % id_or_name)
    return n


@bp.route('/list/', methods=['GET'])
def list_networks():
    return Network.list_networks()


@bp.route('/addr/<path:addr>/available/', methods=['GET'])
def check_addr(addr):
    """addr is like 10.20.0.1/16 or 10.100.3.12/24"""
    try:
        interface = IPNetwork(addr)
    except AddrFormatError:
        abort(400, 'Not valid interface')
    net = Network.get_by_netspace(str(interface.cidr))
    if not net:
        abort(400, 'Interface not found')
    return {'r': 0, 'msg': consts.OK, 'result': interface.ip in net}
