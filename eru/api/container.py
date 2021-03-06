# coding: utf-8
import logging

from flask import request, abort
from netaddr import IPAddress

from .bp import create_api_blueprint, DEFAULT_RETURN_VALUE

from eru.async import dockerjob
from eru.async.task import migrate_container
from eru.consts import ERU_AGENT_DIE_REASON
from eru.helpers.network import rebind_container_ip, bind_container_ip
from eru.ipam import ipam
from eru.models.container import Container, check_eip_bound
from eru.connection import rds
from eru.utils.decorator import check_request_json


bp = create_api_blueprint('container', __name__, url_prefix='/api/container')
_log = logging.getLogger(__name__)


def _get_container(id_or_cid):
    c = None
    if id_or_cid.isdigit():
        c = Container.get(id_or_cid)
    if not c:
        c = Container.get_by_container_id(id_or_cid)
    if not c:
        abort(404, 'Container %s not found' % id_or_cid)
    return c


@bp.route('/<id_or_cid>/', methods=['GET', ])
def get_container(id_or_cid):
    return _get_container(id_or_cid)


@bp.route('/<id_or_cid>/', methods=['DELETE', ])
def remove_container(id_or_cid):
    c = _get_container(id_or_cid)
    dockerjob.remove_container_by_cid([c.container_id], c.host)
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_cid>/kill/', methods=['PUT', ])
def kill_container(id_or_cid):
    c = _get_container(id_or_cid)
    c.kill()

    key = ERU_AGENT_DIE_REASON % c.container_id
    r = rds.get(key)
    rds.delete(key)
    if r is not None:
        c.set_props({'oom': 1})

    c.callback_report(status='die')

    migrate_container.apply_async(args=(c.container_id, True))

    _log.info('Kill container (container_id=%s)', c.container_id)
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_cid>/cure/', methods=['PUT', ])
def cure_container(id_or_cid):
    c = _get_container(id_or_cid)
    c.callback_report(status='start')

    if not c.is_alive:
        rebind_container_ip(c)
        c.cure()

    _log.info('Cure container (container_id=%s)', c.container_id)
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_cid>/poll/', methods=['GET', ])
def poll_container(id_or_cid):
    c = _get_container(id_or_cid)
    return {'container': c.container_id, 'status': c.is_alive}


@bp.route('/<id_or_cid>/start/', methods=['PUT', ])
def start_container(id_or_cid):
    c = _get_container(id_or_cid)
    if not c.is_alive:
        c.cure()
        dockerjob.start_containers([c, ], c.host)
        rebind_container_ip(c)
        _log.info('Start container (container_id=%s)', c.container_id)
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_cid>/stop/', methods=['PUT', ])
def stop_container(id_or_cid):
    c = _get_container(id_or_cid)
    c.kill()
    dockerjob.stop_containers([c,], c.host)
    _log.info('Stop container (container_id=%s)', c.container_id)
    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_cid>/bind_network/', methods=['PUT'])
@check_request_json(['appname', 'networks'])
def bind_network(id_or_cid):
    c = _get_container(id_or_cid)

    data = request.get_json()
    appname = data['appname']

    if not c.is_alive:
        abort(404, 'Container %s not alive' % c.container_id)
    if c.appname != appname:
        abort(404, 'Container does not belong to app')
    if c.network_mode == 'host':
        abort(400, 'Container use host network mode')

    network_names = data.get('networks', [])
    networks = [ipam.get_pool(n) for n in network_names]
    if not networks:
        abort(400, 'network empty')

    cidrs = [n.cidr for n in networks if n]

    bind_container_ip(c, cidrs)
    return {'cidrs': cidrs}


@bp.route('/<id_or_cid>/bind_eip/', methods=['PUT'])
def bind_eip(id_or_cid):
    c = _get_container(id_or_cid)

    data = request.get_json()
    eip = data.get('eip', '')
    eip = IPAddress(eip) if eip else None

    if not c.is_alive:
        abort(404, 'Container %s not alive' % c.container_id)
    if eip and check_eip_bound(eip):
        abort(400, 'EIP already been taken')
    if eip and eip not in c.host.eips:
        abort(400, 'Wrong EIP belonging')

    if not c.bind_eip(eip):
        abort(400, 'No EIP available')

    return DEFAULT_RETURN_VALUE


@bp.route('/<id_or_cid>/release_eip/', methods=['PUT'])
def release_eip(id_or_cid):
    c = _get_container(id_or_cid)

    if not c.is_alive:
        abort(404, 'Container %s not alive' % c.container_id)

    eip = c.eip
    if not eip:
        abort(400, 'Container %s is not bound to EIP' % c.container_id)

    c.release_eip()

    return DEFAULT_RETURN_VALUE
