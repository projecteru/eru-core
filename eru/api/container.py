# coding: utf-8

from flask import current_app, request, abort

from eru import consts
from eru.ipam import ipam
from eru.async import dockerjob
from eru.clients import rds
from eru.models import Container
from eru.helpers.network import rebind_container_ip, bind_container_ip

from .bp import create_api_blueprint

bp = create_api_blueprint('container', __name__, url_prefix='/api/container')


@bp.route('/<id_or_cid>/', methods=['GET', ])
def get_container(id_or_cid):
    c = None
    if id_or_cid.isdigit():
        c = Container.get(int(id_or_cid))
    if not c:
        c = Container.get_by_container_id(id_or_cid)
    if not c:
        abort(404, 'Container %s not found' % id_or_cid)
    return c


@bp.route('/<cid>/', methods=['DELETE', ])
def remove_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        return {'r': 1, 'msg': 'container %s not found' % cid}
    dockerjob.remove_container_by_cid([cid], c.host)
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<cid>/kill', methods=['PUT', ])
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
def cure_container(cid):
    c = Container.get_by_container_id(cid)

    if c:
        c.callback_report(status='start')

        if not c.is_alive:
            rebind_container_ip(c)
            c.cure()

        current_app.logger.info('Cure container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<cid>/poll', methods=['GET', ])
def poll_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        abort(404, 'Container %s not found' % cid)
    return {'r': 0, 'container': c.container_id, 'status': c.is_alive}


@bp.route('/<cid>/start', methods=['PUT', ])
def start_container(cid):
    c = Container.get_by_container_id(cid)
    if c and not c.is_alive:
        c.cure()
        dockerjob.start_containers([c, ], c.host)
        rebind_container_ip(c)
        current_app.logger.info('Start container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<cid>/stop', methods=['PUT', ])
def stop_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
        dockerjob.stop_containers([c,], c.host)
        current_app.logger.info('Stop container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}


@bp.route('/<cid>/bind_network', methods=['PUT'])
def bind_network(cid):
    data = request.get_json()
    appname = data.get('appname')
    c = Container.get_by_container_id(cid)
    if not (c and c.is_alive):
        abort(404, 'Container %s not found' % cid)
    if c.appname != appname:
        abort(404, 'Container does not belong to app')
    if c.network_mode == 'host':
        abort(400, 'Container use host network mode')

    network_names = data.get('networks', [])
    networks = [ipam.get_pool(n) for n in network_names]
    if not networks:
        abort(400, 'network empty')

    cidrs = [n.netspace for n in networks if n]

    bind_container_ip(c, cidrs)
    return {'r': 0, 'msg': cidrs}
