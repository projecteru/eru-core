# coding: utf-8

from flask import Blueprint, g

from eru.models import Pod 
from eru.common import code
from eru.utils.views import jsonify, EruAbortException

bp = Blueprint('pod', __name__, url_prefix='/api/pod')

@bp.route('/<id_or_name>/', methods=['GET'])
@jsonify()
def get_pod(id_or_name):
    if id_or_name.isdigit():
        pod = Pod.get(int(id_or_name))
    else:
        pod = Pod.get_by_name(id_or_name)
    if not pod:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Pod %s not found' % id_or_name)
    return pod

@bp.route('/<id_or_name>/hosts/', methods=['GET'])
@jsonify()
def list_pod_hosts(id_or_name):
    if id_or_name.isdigit():
        pod = Pod.get(int(id_or_name))
    else:
        pod = Pod.get_by_name(id_or_name)
    if not pod:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Pod %s not found' % id_or_name)
    return pod.list_hosts(g.start, g.limit)

@bp.route('/list/', methods=['GET'])
@jsonify()
def list_pods():
    return Pod.list_all(g.start, g.limit)

@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}
