# coding: utf-8

from flask import Blueprint

from eru.common import code
from eru.models import Container
from eru.utils.views import jsonify, EruAbortException
from eru.async import dockerjob
from eru.helpers.network import rebind_container_ip

bp = Blueprint('container', __name__, url_prefix='/api/container')


@bp.route('/<string:cid>/', methods=['GET', ])
@jsonify()
def get_container_by_cid(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Container %s not found' % cid)
    return c


@bp.route('/<int:id>/', methods=['GET', ])
@jsonify()
def get_container_by_id(id):
    c = Container.get(id)
    if not c:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Container %s not found' % id)
    return c


@bp.route('/<cid>/', methods=['DELETE', ])
@jsonify()
def remove_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        return {'r': 1, 'msg': 'container %s not found' % cid}
    dockerjob.remove_container_by_cid([cid], c.host)
    return {'r': 0, 'msg': code.OK}


@bp.route('/<cid>/kill', methods=['PUT', ])
@jsonify()
def kill_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
    return {'r': 0, 'msg': code.OK}


@bp.route('/<cid>/cure', methods=['PUT', ])
@jsonify()
def cure_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        rebind_container_ip(c)
        c.cure()
    return {'r': 0, 'msg': code.OK}


@bp.route('/<cid>/poll', methods=['GET', ])
@jsonify()
def poll_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Container %s not found' % cid)
    return {'r': 0, 'container': c.container_id, 'status': c.is_alive}


@bp.route('/<cid>/start', methods=['PUT', ])
@jsonify()
def start_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.cure()
        dockerjob.start_containers([c, ], c.host)
        rebind_container_ip(c)
    return {'r': 0, 'msg': code.OK}


@bp.route('/<cid>/stop', methods=['PUT', ])
@jsonify()
def stop_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
        dockerjob.stop_containers([c,], c.host)
    return {'r': 0, 'msg': code.OK}


@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}

