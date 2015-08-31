# coding: utf-8

from flask import abort, g, request

from eru.models import Pod 

from .bp import create_api_blueprint


bp = create_api_blueprint('pod', __name__, url_prefix='/api/pod')


def _get_pod(id_or_name):
    if id_or_name.isdigit():
        pod = Pod.get(int(id_or_name))
    else:
        pod = Pod.get_by_name(id_or_name)
    if not pod:
        abort(404, 'Pod %s not found' % id_or_name)
    return pod


@bp.route('/<id_or_name>/', methods=['GET'])
def get_pod(id_or_name):
    return _get_pod(id_or_name)


@bp.route('/<id_or_name>/hosts/', methods=['GET'])
def list_pod_hosts(id_or_name):
    show_all = request.args.get('all', type=bool, default=False)
    pod = _get_pod(id_or_name)
    return pod.list_hosts(g.start, g.limit, show_all=show_all)


@bp.route('/list/', methods=['GET'])
def list_pods():
    return Pod.list_all(g.start, g.limit)
