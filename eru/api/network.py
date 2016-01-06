# coding: utf-8

from flask import abort, request
from netaddr import IPNetwork, AddrFormatError

from eru.ipam import ipam
from eru.utils.decorator import check_request_json

from .bp import create_api_blueprint, DEFAULT_RETURN_VALUE

bp = create_api_blueprint('network', __name__, url_prefix='/api/network')


@bp.route('/create/', methods=['POST'])
@check_request_json(['name', 'cidr'])
def create_network():
    data = request.get_json()
    try:
        cidr = IPNetwork(data['cidr'])
    except AddrFormatError:
        abort(400, 'Not a valid CIDR')

    ipam.add_ip_pool(cidr, data['name'])
    return 201, DEFAULT_RETURN_VALUE


@bp.route('/<id_or_name>/', methods=['GET'])
def get_network(id_or_name):
    n = ipam.get_pool(id_or_name)
    if not n:
        abort(404, 'Network %s not found' % id_or_name)
    return n


@bp.route('/list/', methods=['GET'])
def list_networks():
    return ipam.get_all_pools()


@bp.route('/add_eip/', methods=['POST'])
def add_eip():
    eips = request.get_json()
    try:
        ipam.add_eip(*eips)
    except (AddrFormatError, ValueError):
        abort(400, 'Bad IP format')
    return 201, DEFAULT_RETURN_VALUE


@bp.route('/delete_eip/', methods=['POST'])
def delete_eip():
    eips = request.get_json()
    for eip in eips:
        ipam.get_eip(eip)
    return DEFAULT_RETURN_VALUE


@bp.route('/addr/<path:addr>/available/', methods=['GET'])
def check_addr(addr):
    """addr is like 10.20.0.1/16 or 10.100.3.12/24"""
    try:
        interface = IPNetwork(addr)
    except AddrFormatError:
        abort(400, 'Not valid interface')
    net = ipam.get_pool(str(interface.cidr))
    if not net:
        abort(400, 'Interface not found')
    return {'available': interface.ip in net}
