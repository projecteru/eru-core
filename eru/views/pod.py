# coding: utf-8

from flask import Blueprint, g

from eru.models import Pod 
from eru.common import code
from eru.utils.views import jsonify, EruAbortException

bp = Blueprint('pod', __name__, url_prefix='/api/pod')

@bp.route('/<int:pod_id>/', methods=['GET'])
@jsonify()
def get_pod(pod_id):
    pod = Pod.get(pod_id)
    if not pod:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Pod %s not found' % pod_id)
    return pod

@bp.route('/<string:pod_name>/', methods=['GET'])
@jsonify()
def get_pod_by_name(pod_name):
    pod = Pod.get_by_name(pod_name)
    if not pod:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Pod %s not found' % pod_name)
    return pod

@bp.route('/list/', methods=['GET'])
@jsonify()
def list_pods():
    return Pod.list_all(g.start, g.limit)

@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}
