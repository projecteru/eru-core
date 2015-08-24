# coding:utf-8

import logging

from flask import Blueprint, request, current_app, g

from eru import consts
from eru.config import DEFAULT_CORE_SHARE, DEFAULT_MAX_SHARE_CORE
from eru.models import Group, Pod, Host
from eru.clients import get_docker_client

from eru.utils.decorator import jsonify, check_request_json
from eru.utils.exception import EruAbortException
from eru.helpers.docker import save_docker_certs
from eru.helpers.scheduler import get_max_container_count

bp = Blueprint('sys', __name__, url_prefix='/api/sys')
logger = logging.getLogger(__name__)

@bp.route('/')
@jsonify
def index():
    return {'r': 0, 'msg': consts.OK, 'data': 'sys control'}

@bp.route('/group/create', methods=['POST', ])
@jsonify
@check_request_json('name', consts.HTTP_BAD_REQUEST)
def create_group():
    data = request.get_json()
    if not Group.create(data['name'], data.get('description', '')):
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Group create failed')
    current_app.logger.info('Group create succeeded (name=%s, desc=%s)',
            data['name'], data.get('description', ''))
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/group/list', methods=['GET', ])
@jsonify
def list_groups():
    return Group.list_all(g.start, g.limit)

@bp.route('/group/<id_or_name>/pods/list', methods=['GET', ])
@jsonify
def list_group_pod(id_or_name):
    if id_or_name.isdigit():
        group = Group.get(int(id_or_name))
    else:
        group = Group.get_by_name(id_or_name)
    if not group:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Group %s not found' % id_or_name)
    return group.list_pods(g.start, g.limit)

@bp.route('/pod/create', methods=['POST', ])
@jsonify
@check_request_json('name', consts.HTTP_BAD_REQUEST)
def create_pod():
    data = request.get_json()
    if not Pod.create(
            data['name'],
            data.get('description', ''),
            data.get('core_share', DEFAULT_CORE_SHARE),
            data.get('max_share_core', DEFAULT_MAX_SHARE_CORE),
    ):
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Pod create failed')
    current_app.logger.info('Pod create succeeded (name=%s, desc=%s)',
            data['name'], data.get('description', ''))
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/pod/<pod_name>/assign', methods=['POST', ])
@jsonify
@check_request_json('group_name', consts.HTTP_BAD_REQUEST)
def assign_pod_to_group(pod_name):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    pod = Pod.get_by_name(pod_name)
    if not group or not pod:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'No group/pod found')

    if not pod.assigned_to_group(group):
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Assign failed')
    current_app.logger.info('Pod (name=%s) assigned to group (name=%s)',
            pod_name, data['group_name'])
    return {'r':0, 'msg': consts.OK}

@bp.route('/host/create', methods=['POST', ])
@jsonify
def create_host():
    """为了文件, 只好不用json了"""
    addr = request.form.get('addr', default='')
    pod_name = request.form.get('pod_name', default='')
    if not (addr and pod_name):
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'need addr and pod_name')

    pod = Pod.get_by_name(pod_name)
    if not pod:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'No pod found')

    # 存证书, 没有就算了
    try:
        ca, cert, key = request.files['ca'], request.files['cert'], request.files['key']
        save_docker_certs(addr.split(':', 1)[0], ca.read(), cert.read(), key.read())
    finally:
        ca.close()
        cert.close()
        key.close()

    try:
        client = get_docker_client(addr, force_flush=True)
        info = client.info()
    except Exception:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Docker daemon error on host %s' % addr)

    if not Host.create(pod, addr, info['Name'], info['ID'], info['NCPU'], info['MemTotal']):
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/host/<addr>/assign', methods=['POST', ])
@jsonify
@check_request_json('group_name', consts.HTTP_BAD_REQUEST)
def assign_host_to_group(addr):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    if not group:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'No group found')

    host = Host.get_by_addr(addr)
    if not host:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'No host found')

    if not host.assigned_to_group(group):
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Assign failed')
    current_app.logger.info('Host (addr=%s) assigned to group (name=%s)',
            addr, data['group_name'])
    return {'r':0, 'msg': consts.OK}

@bp.route('/group/<group_name>/available_container_count', methods=['GET', ])
@jsonify
def group_max_containers(group_name):
    pod_name = request.args.get('pod_name', default='')
    core_require = request.args.get('ncore', type=float, default=1)

    group = Group.get_by_name(group_name)
    if not group:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'No group found')
    pod = Pod.get_by_name(pod_name)
    if not pod:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'No pod found')

    core_require = int(core_require * pod.core_share) # 是说一个容器要几个核...
    ncore = core_require / pod.core_share
    nshare = core_require % pod.core_share

    return {'r':0, 'msg': consts.OK, 'data': get_max_container_count(group, pod, ncore, nshare)}
