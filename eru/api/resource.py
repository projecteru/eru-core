# coding: utf-8

from flask import abort

from eru.models import Host, Pod

from .bp import create_api_blueprint


bp = create_api_blueprint('resource', __name__, url_prefix='/api/resource')


@bp.route('/host/<host_id>/resource/')
def get_host_resource(host_id):
    host = Host.get(host_id)
    if not host:
        abort(404, 'Host %s not found' % host_id)

    core_count = len(host.cores)
    fe, fs = host.get_free_cores()
    return {
        'core_count': core_count,
        'free_excluded_cores': [c.label for c in fe],
        'free_shared_cores': [c.label for c in fs],
        'memory': host.mem,
    }


@bp.route('/pod/<pod_id>/resource/')
def get_pod_resource(pod_id):
    pod = Pod.get(pod_id)
    if not pod:
        abort(404, 'Pod %s not found' % pod_id)

    core_count = sum(len(h.cores) for h in pod.hosts.all())
    free_excluded_cores = [c for h in pod.hosts.all() for c in h.get_free_cores()[0]]
    free_shared_cores = [c for h in pod.hosts.all() for c in h.get_free_cores()[1]]
    return {
        'core_count': core_count,
        'free_excluded_cores': [c.label for c in free_excluded_cores],
        'free_shared_cores': [c.label for c in free_shared_cores],
    }
