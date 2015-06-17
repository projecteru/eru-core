#!/usr/bin/python
#coding:utf-8

import logging

from flask import Blueprint, request, current_app

from eru import consts
from eru.clients import get_docker_client
from eru.config import DEFAULT_CORE_SHARE, DEFAULT_MAX_SHARE_CORE
from eru.models import Group, Pod, Host
from eru.utils.decorator import jsonify, check_request_json
from eru.utils.exception import EruAbortException

bp = Blueprint('sys', __name__, url_prefix='/api/sys')
logger = logging.getLogger(__name__)

@bp.route('/')
@jsonify
def index():
    return {'r': 0, 'msg': consts.OK, 'data': 'sys control'}

@bp.route('/group/create', methods=['POST', ])
@check_request_json('name', consts.HTTP_BAD_REQUEST)
@jsonify
def create_group():
    data = request.get_json()
    if not Group.create(data['name'], data.get('description', '')):
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    current_app.logger.info('Group create succeeded (name=%s, desc=%s)',
            data['name'], data.get('description', ''))
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/pod/create', methods=['POST', ])
@check_request_json('name', consts.HTTP_BAD_REQUEST)
@jsonify
def create_pod():
    data = request.get_json()
    if not Pod.create(
            data['name'],
            data.get('description', ''),
            data.get('core_share', DEFAULT_CORE_SHARE),
            data.get('max_share_core', DEFAULT_MAX_SHARE_CORE),
    ):
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    current_app.logger.info('Pod create succeeded (name=%s, desc=%s)',
            data['name'], data.get('description', ''))
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/pod/<pod_name>/assign', methods=['POST', ])
@check_request_json('group_name', consts.HTTP_BAD_REQUEST)
@jsonify
def assign_pod_to_group(pod_name):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    pod = Pod.get_by_name(pod_name)
    if not group or not pod:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)

    if not pod.assigned_to_group(group):
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    current_app.logger.info('Pod (name=%s) assigned to group (name=%s)',
            pod_name, data['group_name'])
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/host/create', methods=['POST', ])
@check_request_json(['addr', 'pod_name'], consts.HTTP_BAD_REQUEST)
@jsonify
def create_host():
    data = request.get_json()
    addr = data['addr']

    pod = Pod.get_by_name(data['pod_name'])
    if not pod:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)

    try:
        client = get_docker_client(addr)
        info = client.info()
    except Exception:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Docker daemon error on host %s' % addr)

    if not Host.create(pod, addr, info['Name'], info['ID'], info['NCPU'], info['MemTotal']):
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/host/<addr>/assign', methods=['POST', ])
@check_request_json('group_name', consts.HTTP_BAD_REQUEST)
@jsonify
def assign_host_to_group(addr):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    if not group:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)

    host = Host.get_by_addr(addr)
    if not host:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)

    if not host.assigned_to_group(group):
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    current_app.logger.info('Host (addr=%s) assigned to group (name=%s)',
            addr, data['group_name'])
    return consts.HTTP_CREATED, {'r':0, 'msg': consts.OK}

@bp.route('/group/<group_name>/available_container_count', methods=['GET', ])
@jsonify
def group_max_containers(group_name):
    pod_name = request.args.get('pod_name', type=str, default='')
    core_require = request.args.get('ncore', type=float, default=1)

    group = Group.get_by_name(group_name)
    if not group:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    pod = Pod.get_by_name(pod_name)
    if not pod:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)

    core_require = int(core_require * pod.core_share) # 是说一个容器要几个核...
    ncore = core_require / pod.core_share
    nshare = core_require % pod.core_share

    return {'r':0, 'msg': consts.OK, 'data': group.get_max_containers(pod, ncore, nshare)}
