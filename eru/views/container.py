# coding: utf-8

from flask import Blueprint, abort

from eru.common import code
from eru.models import Container
from eru.utils.views import jsonify


bp = Blueprint('container', __name__, url_prefix='/api/container')


@bp.route('/<cid>/kill', methods=['PUT', ])
@jsonify
def kill_container(cid):
    c = Container.get_by_container_id(cid)
    if c:
        c.kill()
    return {'r':0, 'msg': code.OK}


@bp.route('/<cid>/poll', methods=['GET', ])
@jsonify
def poll_container(cid):
    c = Container.get_by_container_id(cid)
    if not c:
        abort(404)
    return {'r':0, 'container': c.container_id, 'status': c.is_alive}


@bp.errorhandler(404)
@jsonify
def not_found_handler(exception):
    return {'r': 1, 'msg': str(exception.code)}

