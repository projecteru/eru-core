#!/usr/bin/python
#coding:utf-8

import logging

from flask import Blueprint, request, abort

from eru.common import code
from eru.common.clients import get_docker_client
from eru.models import Group, Pod, Host
from eru.utils.views import jsonify, check_request_json


bp = Blueprint('sys', __name__, url_prefix='/api/sys')
logger = logging.getLogger(__name__)


@bp.route('/')
def index():
    return 'sys control'


@bp.route('/group/create', methods=['POST', ])
@check_request_json('name', code.HTTP_BAD_REQUEST)
@jsonify(code.HTTP_CREATED)
def create_group():
    data = request.get_json()
    if not Group.create(data['name'], data.get('description', '')):
        abort(code.HTTP_BAD_REQUEST)
    return {'r':0, 'msg': code.OK}


@bp.route('/pod/create', methods=['POST', ])
@check_request_json('name', code.HTTP_BAD_REQUEST)
@jsonify(code.HTTP_CREATED)
def create_pod():
    data = request.get_json()
    if not Pod.create(data['name'], data.get('description', '')):
        abort(code.HTTP_BAD_REQUEST)
    return {'r':0, 'msg': code.OK}


@bp.route('/pod/<pod_name>/assign', methods=['POST', ])
@check_request_json('group_name', code.HTTP_BAD_REQUEST)
@jsonify(code.HTTP_CREATED)
def assign_pod_to_group(pod_name):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    pod = Pod.get_by_name(pod_name)
    if not group or not pod:
        abort(code.HTTP_BAD_REQUEST)

    if not pod.assigned_to_group(group):
        abort(code.HTTP_BAD_REQUEST)
    return {'r':0, 'msg': code.OK}


@bp.route('/host/create', methods=['POST', ])
@check_request_json(['addr', 'pod_name'], code.HTTP_BAD_REQUEST)
@jsonify(code.HTTP_CREATED)
def create_host():
    data = request.get_json()
    addr = data['addr']

    pod = Pod.get_by_name(data['pod_name'])
    if not pod:
        abort(code.HTTP_BAD_REQUEST)

    client = get_docker_client(addr)
    info = client.info()
    if not Host.create(pod, addr, info['Name'], info['ID'], info['NCPU'], info['MemTotal']):
        abort(code.HTTP_BAD_REQUEST)
    return {'r':0, 'msg': code.OK}


@bp.route('/host/<addr>/assign', methods=['POST', ])
@check_request_json('group_name', code.HTTP_BAD_REQUEST)
@jsonify(code.HTTP_CREATED)
def assign_host_to_group(addr):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    if not group:
        abort(code.HTTP_BAD_REQUEST)

    host = Host.get_by_addr(addr)
    if not host:
        abort(code.HTTP_BAD_REQUEST)

    if not host.assigned_to_group(group):
        abort(code.HTTP_BAD_REQUEST)
    return {'r':0, 'msg': code.OK}


@bp.route('/group/<group_name>/available_container_count', methods=['GET', ])
@jsonify()
def group_max_containers(group_name):
    pod_name = request.args.get('pod_name', type=str, default='')
    cores_per_container = request.args.get('ncore', type=int, default=1)

    group = Group.get_by_name(group_name)
    if not group:
        abort(code.HTTP_BAD_REQUEST)
    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(code.HTTP_BAD_REQUEST)

    return {'r':0, 'msg': code.OK, 'data': group.get_max_containers(pod, cores_per_container)}


@bp.route('/alloc/<res_name>', methods=['POST', ])
@jsonify(code.HTTP_CREATED)
def alloc_resource(res_name):
    r = RESOURCES.get(res_name)
    if not r:
        abort(code.HTTP_BAD_REQUEST)

    try:
        mod = import_string(r)
        data = request.get_json()
        return {'r':0, 'msg': code.OK, 'data': mod.alloc(**data)}
    except Exception, e:
        logger.exception(e)
        abort(code.HTTP_BAD_REQUEST)

