# coding: utf-8

from flask import Blueprint

from eru import consts
from eru.models import Host, Pod
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException

bp = Blueprint('resource', __name__, url_prefix='/api/resource')

@bp.route('/host/<host_id>/resource/')
@jsonify
def get_host_resource(host_id):
    host = Host.get(host_id)
    if not host:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Host %s not found' % host_id)
    core_count = len(host.cores)
    fe, fs = host.get_free_cores()
    return {
        'core_count': core_count,
        'free_excluded_cores': [c.label for c in fe],
        'free_shared_cores': [c.label for c in fs],
        'memory': host.mem,
    }

@bp.route('/pod/<pod_id>/resource/')
@jsonify
def get_pod_resource(pod_id):
    pod = Pod.get(pod_id)
    if not pod:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Pod %s not found' % pod_id)
    core_count = sum(len(h.cores) for h in pod.hosts.all())
    free_excluded_cores = [c for h in pod.hosts.all() for c in h.get_free_cores()[0]]
    free_shared_cores = [c for h in pod.hosts.all() for c in h.get_free_cores()[1]]
    return {
        'core_count': core_count,
        'free_excluded_cores': [c.label for c in free_excluded_cores],
        'free_shared_cores': [c.label for c in free_shared_cores],
    }
