# coding: utf-8

from flask import Blueprint, current_app, request

from eru import consts
from eru.clients import rds
from eru.async import dockerjob
from eru.models import Container, Network
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException
from eru.helpers.network import rebind_container_ip, bind_container_ip

bp = Blueprint('container', __name__, url_prefix='/api/container')

@bp.route('/<string:cid>/', methods=['GET', ])
@jsonify
def get_container_by_cid(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Container %s not found' % cid)
    return c

@bp.route('/<int:id>/', methods=['GET', ])
@jsonify
def get_container_by_id(id):
    c = Container.get(id)
    if not c:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Container %s not found' % id)
    return c

@bp.route('/<cid>/', methods=['DELETE', ])
@jsonify
def remove_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        return {'r': 1, 'msg': 'container %s not found' % cid}
    dockerjob.remove_container_by_cid([cid], c.host)
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<cid>/kill', methods=['PUT', ])
@jsonify
def kill_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
        key = consts.ERU_AGENT_DIE_REASON % c.container_id
        r = rds.get(key)
        rds.delete(key)
        if r is not None:
            c.set_props({'oom': 1})

        c.callback_report(status='die')

        current_app.logger.info('Kill container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<cid>/cure', methods=['PUT', ])
@jsonify
def cure_container(cid):
    c = Container.get_by_container_id(cid)

    if c:
        c.callback_report(status='start')

    if c and not c.is_alive:
        rebind_container_ip(c)
        c.cure()

        current_app.logger.info('Cure container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<cid>/poll', methods=['GET', ])
@jsonify
def poll_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Container %s not found' % cid)
    return {'r': 0, 'container': c.container_id, 'status': c.is_alive}

@bp.route('/<cid>/start', methods=['PUT', ])
@jsonify
def start_container(cid):
    c = Container.get_by_container_id(cid)
    if c and not c.is_alive:
        c.cure()
        dockerjob.start_containers([c, ], c.host)
        rebind_container_ip(c)
        current_app.logger.info('Start container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<cid>/stop', methods=['PUT', ])
@jsonify
def stop_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
        dockerjob.stop_containers([c,], c.host)
        current_app.logger.info('Stop container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<cid>/bind_network', methods=['PUT'])
@jsonify
def bind_network(cid):
    data = request.get_json()
    appname = data.get('appname')
    c = Container.get_by_container_id(cid)
    if not (c and c.is_alive):
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Container %s not found' % cid)
    if c.appname != appname:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Container does not belong to app')

    network_names = data.get('networks', [])
    networks = filter(None, [Network.get_by_name(n) for n in network_names])
    if not networks:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'network empty')

    ips = filter(None, [n.acquire_ip() for n in networks])
    if not ips:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'no ip available')

    nid = max([ip.network_id for ip in c.ips.all()] + [-1]) + 1
    bind_container_ip(c, ips, nid=nid)
    for ip in ips:
        ip.assigned_to_container(c)
    return {'r': 0, 'msg': ips}
