# coding: utf-8

from flask import Blueprint

from eru.common import code
from eru.models import Container
from eru.utils.views import jsonify, EruAbortException


bp = Blueprint('container', __name__, url_prefix='/api/container')


@bp.route('/<cid>/kill', methods=['PUT', ])
@jsonify()
def kill_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
    return {'r':0, 'msg': code.OK}


@bp.route('/<cid>/poll', methods=['GET', ])
@jsonify()
def poll_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Container %s not found' % cid)
    return {'r':0, 'container': c.container_id, 'status': c.is_alive}


@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}

