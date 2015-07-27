# coding: utf-8

from flask import Blueprint, current_app, request

from eru import consts
from eru.async import dockerjob
from eru.models import Container
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException
from eru.helpers.network import rebind_container_ip

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
        data = request.get_json()
        if data:
            c.set_props(**data)
        current_app.logger.info('Kill container (container_id=%s)', cid[:7])
    return {'r': 0, 'msg': consts.OK}

@bp.route('/<cid>/cure', methods=['PUT', ])
@jsonify
def cure_container(cid):
    c = Container.get_by_container_id(cid)
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
