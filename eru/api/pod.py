# coding: utf-8

import logging
from flask import abort, g, request

from eru.models import Pod 
from eru.utils.decorator import check_request_json
from eru.config import DEFAULT_CORE_SHARE, DEFAULT_MAX_SHARE_CORE
from .bp import create_api_blueprint, DEFAULT_RETURN_VALUE

bp = create_api_blueprint('pod', __name__, url_prefix='/api/pod')
_log = logging.getLogger(__name__)


def _get_pod(id_or_name):
    pod = Pod.get(id_or_name) or Pod.get_by_name(id_or_name)
    if not pod:
        abort(404, 'Pod %s not found' % id_or_name)
    return pod


@bp.route('/<id_or_name>/', methods=['GET'])
def get_pod(id_or_name):
    return _get_pod(id_or_name)


@bp.route('/create/', methods=['POST'])
@check_request_json('name')
def create_pod():
    data = request.get_json()
    if not Pod.create(
            data['name'],
            data.get('description', ''),
            data.get('core_share', DEFAULT_CORE_SHARE),
            data.get('max_share_core', DEFAULT_MAX_SHARE_CORE),
    ):
        abort(400, 'Pod create failed')
    _log.info('Pod create succeeded (name=%s, desc=%s)', data['name'], data.get('description', ''))
    return 201, DEFAULT_RETURN_VALUE


@bp.route('/<id_or_name>/hosts/', methods=['GET'])
def list_pod_hosts(id_or_name):
    show_all = request.args.get('all', type=bool, default=False)
    pod = _get_pod(id_or_name)
    return pod.list_hosts(g.start, g.limit, show_all=show_all)


@bp.route('/list/', methods=['GET'])
def list_pods():
    return Pod.list_all(g.start, g.limit)
