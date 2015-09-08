# coding:utf-8

from flask import abort, request, current_app, g

from eru import consts
from eru.config import DEFAULT_CORE_SHARE, DEFAULT_MAX_SHARE_CORE
from eru.models import Group, Pod, Host
from eru.clients import get_docker_client

from eru.utils.decorator import check_request_json
from eru.helpers.docker import save_docker_certs
from eru.helpers.scheduler import get_max_container_count

from .bp import create_api_blueprint


bp = create_api_blueprint('sys', __name__, url_prefix='/api/sys')


@bp.route('/group/create', methods=['POST', ])
@check_request_json('name')
def create_group():
    data = request.get_json()
    if not Group.create(data['name'], data.get('description', '')):
        abort(400, 'Group create failed')
    current_app.logger.info('Group create succeeded (name=%s, desc=%s)',
            data['name'], data.get('description', ''))
    return 201, {'r': 0, 'msg': consts.OK}


@bp.route('/group/list', methods=['GET', ])
def list_groups():
    return Group.list_all(g.start, g.limit)


@bp.route('/group/<id_or_name>/pods/list', methods=['GET', ])
def list_group_pod(id_or_name):
    if id_or_name.isdigit():
        group = Group.get(int(id_or_name))
    else:
        group = Group.get_by_name(id_or_name)
    if not group:
        abort(404, 'Group %s not found' % id_or_name)
    return group.list_pods(g.start, g.limit)


@bp.route('/pod/create', methods=['POST', ])
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
    current_app.logger.info('Pod create succeeded (name=%s, desc=%s)',
            data['name'], data.get('description', ''))
    return 201, {'r':0, 'msg': consts.OK}


@bp.route('/pod/<pod_name>/assign', methods=['POST', ])
@check_request_json('group_name')
def assign_pod_to_group(pod_name):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    pod = Pod.get_by_name(pod_name)
    if not group or not pod:
        abort(404, 'No group/pod found')

    if not pod.assigned_to_group(group):
        abort(400, 'Assign failed')
    current_app.logger.info('Pod (name=%s) assigned to group (name=%s)',
            pod_name, data['group_name'])
    return {'r':0, 'msg': consts.OK}


@bp.route('/host/create', methods=['POST', ])
def create_host():
    """为了文件, 只好不用json了"""
    addr = request.form.get('addr', default='')
    pod_name = request.form.get('pod_name', default='')
    if not (addr and pod_name):
        abort(400, 'Need addr and pod_name')

    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(400, 'No pod found')

    # 存证书, 没有就算了
    if all(k in request.files for k in ['ca', 'cert', 'key']):
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
    except Exception as e:
        abort(400, 'Docker daemon error on host %s, error: %s' % (addr, e.message))

    if not Host.create(pod, addr, info['Name'], info['ID'], info['NCPU'], info['MemTotal']):
        abort(400, 'Host create error.')
    return 201, {'r':0, 'msg': consts.OK}


@bp.route('/host/<addr>/assign', methods=['POST', ])
@check_request_json('group_name')
def assign_host_to_group(addr):
    data = request.get_json()

    group = Group.get_by_name(data['group_name'])
    if not group:
        abort(400, 'No group found')

    host = Host.get_by_addr(addr)
    if not host:
        abort(400, 'No host found')

    if not host.assigned_to_group(group):
        abort(400, 'Assign failed')
    current_app.logger.info('Host (addr=%s) assigned to group (name=%s)',
            addr, data['group_name'])
    return {'r':0, 'msg': consts.OK}


@bp.route('/group/<group_name>/available_container_count', methods=['GET', ])
def group_max_containers(group_name):
    pod_name = request.args.get('pod_name', default='')
    core_require = request.args.get('ncore', type=float, default=1)

    group = Group.get_by_name(group_name)
    if not group:
        abort(400, 'No group found')
    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(400, 'No pod found')

    ncore, nshare = pod.get_core_allocation(core_require)
    return {'r':0, 'msg': consts.OK, 'data': get_max_container_count(group, pod, ncore, nshare)}
