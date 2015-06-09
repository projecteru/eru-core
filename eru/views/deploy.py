#!/usr/bin/python
#coding:utf-8

import logging
import itertools

from flask import Blueprint, request, current_app

from eru.async.task import create_containers_with_macvlan, build_docker_image, remove_containers
from eru.common import code
from eru.common.clients import rds
from eru.models import App, Group, Pod, Task, Network, Container, Host
from eru.utils.views import check_request_json, jsonify, EruAbortException

bp = Blueprint('deploy', __name__, url_prefix='/api/deploy')
logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    return 'deploy control'

@bp.route('/private/<group_name>/<pod_name>/<appname>', methods=['POST', ])
@check_request_json(['ncore', 'ncontainer', 'version', 'entrypoint', 'env'])
@jsonify()
def create_private(group_name, pod_name, appname):
    """ncore: 需要的核心数, 可以是小数, 例如1.5个"""
    data = request.get_json()

    if data.get('raw', ''):
        vstr = code.RAW_VERSION_PLACEHOLDER
    else:
        vstr = data['version']

    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, vstr)

    # TODO check if group has this pod

    core_require = int(float(data['ncore']) * pod.core_share) # 是说一个容器要几个核...
    ncore = core_require / pod.core_share
    nshare = core_require % pod.core_share

    ncontainer = int(data['ncontainer'])
    networks = Network.get_multi(data.get('networks', []))
    appconfig = version.appconfig

    # 指定的host, 如果没有则按照编排分配host
    hostname = data.get('hostname', '')
    host = hostname and Host.get_by_name(hostname) or None
    if host and not (host.group_id == group.id and host.pod_id == pod.id):
        current_app.logger.error('Host must belong to pod/group (hostname=%s, pod=%s, group=%s)',
                host, pod_name, group_name)
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Host must belong to this pod and group')

    if not data['entrypoint'] in appconfig.entrypoints:
        current_app.logger.error('Entrypoint not in app.yaml (entry=%s, name=%s, version=%s)',
                data['entrypoint'], appname, version.short_sha)
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Entrypoint %s not in app.yaml' % data['entrypoint'])

    ts, keys = [], []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        host_cores = group.get_free_cores(pod, ncontainer, ncore, nshare, spec_host=host)
        if not host_cores:
            current_app.logger.error('Not enough cores (name=%s, version=%s, ncore=%s)',
                    appname, version.short_sha, data['ncore'])
            raise EruAbortException(code.HTTP_BAD_REQUEST, 'Not enough core resources')

        for (host, container_count), cores in host_cores.iteritems():
            t = _create_task(code.TASK_CREATE, version, host, container_count,
                    cores, nshare, networks, data['entrypoint'], data['env'],
                    image=data.get('image', ''))
            if not t:
                continue

            host.occupy_cores(cores, nshare)
            ts.append(t.id)
            keys.append(t.result_key)

    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}

@bp.route('/public/<group_name>/<pod_name>/<appname>', methods=['POST', ])
@check_request_json(['ncontainer', 'version', 'entrypoint', 'env'])
@jsonify()
def create_public(group_name, pod_name, appname):
    """参数同private, 只是不能指定需要的核心数量"""
    data = request.get_json()

    if data.get('raw', ''):
        vstr = code.RAW_VERSION_PLACEHOLDER
    else:
        vstr = data['version']

    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, vstr)

    networks = Network.get_multi(data.get('networks', []))
    ncontainer = int(data['ncontainer'])
    appconfig = version.appconfig
    if not data['entrypoint'] in appconfig.entrypoints:
        current_app.logger.error('Entrypoint not in app.yaml (entry=%s, name=%s, version=%s)',
                data['entrypoint'], appname, version.short_sha)
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Entrypoint %s not in app.yaml' % data['entrypoint'])

    ts, keys = [], []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        hosts = pod.get_free_public_hosts(ncontainer)
        for host in itertools.islice(itertools.cycle(hosts), ncontainer):
            t = _create_task(code.TASK_CREATE, version, host, 1,
                    {}, 0, networks, data['entrypoint'], data['env'],
                    image=data.get('image', ''))
            if not t:
                continue
            ts.append(t.id)
            keys.append(t.result_key)

    return {'r':0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}

@bp.route('/build/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['base', 'version'])
@jsonify()
def build_image(group_name, pod_name, appname):
    data = request.get_json()
    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])
    # TODO
    # 这个group可以用这个pod不?
    # 这个group可以build这个version不?
    base = data['base']
    host = pod.get_random_host()
    task = Task.create(code.TASK_BUILD, version, host, {'base': base})
    build_docker_image.apply_async(
        args=(task.id, base),
        task_id='task:%d' % task.id
    )
    return {'r': 0, 'msg': 'ok', 'task': task.id, 'watch_key': task.result_key}

@bp.route('/rmcontainers/', methods=['PUT', 'POST', ])
@check_request_json(['cids'])
@jsonify()
def rm_containers():
    cids = request.get_json()['cids']
    version_dict = {}
    ts, watch_keys = [], []
    for cid in cids:
        container = Container.get_by_container_id(cid)
        if not container:
            continue
        version_dict.setdefault((container.version, container.host), []).append(container)
    for (version, host), containers in version_dict.iteritems():
        cids = [c.id for c in containers]
        task_props = {'container_ids': cids}
        task = Task.create(code.TASK_REMOVE, version, host, task_props)
        remove_containers.apply_async(
            args=(task.id, cids, False),
            task_id='task:%d' % task.id
        )
        ts.append(task.id)
        watch_keys.append(task.result_key)
    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': watch_keys}

@bp.route('/rmversion/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['version'])
@jsonify()
def offline_version(group_name, pod_name, appname):
    data = request.get_json()
    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])
    d = {}
    ts, keys = [], []
    for container in version.containers.all():
        d.setdefault(container.host, []).append(container)
    for host, containers in d.iteritems():
        cids = [c.id for c in containers]
        task_props = {'container_ids': cids}
        task = Task.create(code.TASK_REMOVE, version, host, task_props)
        remove_containers.apply_async(
            args=(task.id, cids, True),
            task_id='task:%d' % task.id
        )
        ts.append(task.id)
        keys.append(task.result_key)
    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}

def validate_instance(group_name, pod_name, appname, version):
    group = Group.get_by_name(group_name)
    if not group:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Group `%s` not found' % group_name)

    pod = Pod.get_by_name(pod_name)
    if not pod:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Pod `%s` not found' % pod_name)

    application = App.get_by_name(appname)
    if not application:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'App `%s` not found' % appname)

    version = application.get_version(version)
    if not version:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Version `%s` not found' % version)

    return group, pod, application, version

def _create_task(type_, version, host, ncontainer,
    cores, nshare, networks, entrypoint, env, image=''):
    network_ids = [n.id for n in networks]
    task_props = {
        'ncontainer': ncontainer,
        'entrypoint': entrypoint,
        'env': env,
        'full_cores': [c.label for c in cores.get('full', [])],
        'part_cores': [c.label for c in cores.get('part', [])],
        'nshare': nshare,
        'networks': network_ids,
        'image': image,
    }
    task = Task.create(type_, version, host, task_props)
    if not task:
        return None

    try:
        create_containers_with_macvlan.apply_async(
            args=(task.id, ncontainer, nshare, cores, network_ids),
            task_id='task:%d' % task.id
        )
    except Exception as e:
        logger.exception(e)
        host.release_cores(cores)

    return task

@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}
