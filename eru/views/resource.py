# coding: utf-8

from flask import Blueprint

from eru.models import Host, Pod
from eru.common import code
from eru.utils.views import jsonify, EruAbortException

bp = Blueprint('resource', __name__, url_prefix='/api/resource')


@bp.route('/host/<host_id>/resource/')
@jsonify()
def get_host_resource(host_id):
    host = Host.get(host_id)
    if not host:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Host %s not found' % host_id)
    core_count = len(host.cores.all())
    free_cores = host.get_free_cores()
    return {
        'core_count': core_count,
        'free_cores': [c.label for c in free_cores],
        'memory': host.mem,
    }


@bp.route('/pod/<pod_id>/resource/')
@jsonify()
def get_pod_resource(pod_id):
    pod = Pod.get(pod_id)
    if not pod:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Pod %s not found' % pod_id)
    core_count = sum(len(h.cores.all()) for h in pod.hosts.all())
    free_cores = [c for h in pod.hosts.all() for c in h.get_free_cores()]
    return {
        'core_count': core_count,
        'free_cores': [c.label for c in free_cores],
    }


@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}
