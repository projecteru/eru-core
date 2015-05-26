#!/usr/bin/python
#coding:utf-8

import logging
import itertools

from flask import Blueprint, request

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

@bp.route('/private/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['ncore', 'ncontainer', 'version', 'entrypoint', 'env'])
@jsonify()
def create_private(group_name, pod_name, appname):
    """
    ncore: int cpu num per container -1 means share, support x.x
    ncontainer: int container nums
    version: string deploy version
    expose: bool true or false, default true
    """
    data = request.get_json()
    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])

    # TODO check if group has this pod

    core_require = int(float(data['ncore']) * pod.core_share) # 是说一个容器要几个核...
    ncore = core_require / pod.core_share
    nshare = core_require % pod.core_share

    ncontainer = int(data['ncontainer'])
    networks = Network.get_multi(data.get('networks', []))
    appconfig = version.appconfig

    if not data['entrypoint'] in appconfig.entrypoints:
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Entrypoint %s not in app.yaml' % data['entrypoint'])

    tasks_info = []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        # 分配时不够直接raise
        host_cores = group.get_free_cores(pod, ncontainer, ncore, nshare)
        if not host_cores:
            raise EruAbortException(code.HTTP_BAD_REQUEST, 'Not enough core resources')

        try:
            for (host, container_count), cores in host_cores.iteritems():
                tasks_info.append(
                    (version, host, container_count, cores, nshare, networks, data['entrypoint'], data['env'])
                )
                host.occupy_cores(cores, nshare)
        except Exception, e:
            logger.exception(e)
            raise EruAbortException(code.HTTP_BAD_REQUEST, str(e))

    ts, keys = [], []
    for task_info in tasks_info:
        #create_task will always correct
        t = _create_task(code.TASK_CREATE, *task_info)
        if not t:
            continue
        ts.append(t.id)
        keys.append(t.result_key)

    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}

@bp.route('/public/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['ncontainer', 'version', 'entrypoint', 'env'])
@jsonify()
def create_public(group_name, pod_name, appname):
    """
    ncontainer: int container nums
    version: string deploy version
    expose: bool true or false, default true
    """
    data = request.get_json()

    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])

    networks = Network.get_multi(data.get('networks', []))
    ncontainer = int(data['ncontainer'])
    appconfig = version.appconfig
    if not data['entrypoint'] in appconfig.entrypoints:
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Entrypoint %s not in app.yaml' % data['entrypoint'])

    tasks_info = []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        try:
            # 轮询, 尽可能均匀部署
            hosts = pod.get_free_public_hosts(ncontainer)
            for host in itertools.islice(itertools.cycle(hosts), ncontainer):
                tasks_info.append(
                    (version, host, 1, {}, networks, data['entrypoint'], data['env'])
                )
        except Exception, e:
            logger.exception(e)
            raise EruAbortException(code.HTTP_BAD_REQUEST, str(e))

    ts, keys = [], []
    for task_info in tasks_info:
        #create_task will always correct
        t = _create_task(code.TASK_CREATE, *task_info)
        if not t:
            continue
        ts.append(t.id)
        keys.append(t.result_key)

    return {'r':0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}

@bp.route('/onhost/', methods=['POST'])
@check_request_json(['ncontainer', 'version',
    'entrypoint', 'env', 'hostname', 'appname', 'ncore'])
@jsonify()
def create_container_on_host():
    data = request.get_json()
    host = Host.get_by_name(data['hostname'])
    if not host:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Host not found')
    if not host.group:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Host must be private')
    app = App.get_by_name(data['appname'])
    if not app:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'App `%s` not found' % data['appname'])
    version = app.get_version(data['version'])
    if not version:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Version `%s` not found' % data['version'])

    group, pod = host.group, host.pod

    # TODO
    # 这个 host 可以给当前的 user 玩不?

    core_require = int(float(data['ncore']) * pod.core_share) # 是说一个容器要几个核...
    ncore = core_require / pod.core_share
    nshare = core_require % pod.core_share

    ncontainer = int(data['ncontainer'])
    networks = Network.get_multi(data.get('networks', []))
    appconfig = version.appconfig

    if not data['entrypoint'] in appconfig.entrypoints:
        raise EruAbortException(code.HTTP_BAD_REQUEST,
                'Entrypoint %s not in app.yaml' % data['entrypoint'])

    ts, keys = [], []
    with rds.lock('{0}:{1}'.format(group.name, pod.name)):
        host_cores = group.get_free_cores(pod, ncontainer, ncore, nshare, spec_host=host)
        if not host_cores:
            raise EruAbortException(code.HTTP_BAD_REQUEST, 'Not enough core resources')
        for (host, container_count), cores in host_cores.iteritems():
            host.occupy_cores(cores, nshare)
            t = _create_task(code.TASK_CREATE, version, host, container_count, cores,
                    nshare, networks, data['entrypoint'], data['env'])
            ts.append(t.id)
            keys.append(t.result_key)
    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}

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
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Group `%s` not found' % group_name)

    pod = Pod.get_by_name(pod_name)
    if not pod:
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Pod `%s` not found' % pod_name)

    application = App.get_by_name(appname)
    if not application:
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'App `%s` not found' % appname)

    version = application.get_version(version)
    if not version:
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Version `%s` not found' % version)

    return group, pod, application, version

def _create_task(type_, version, host, ncontainer, cores, nshare, networks, entrypoint, env):
    try:
        network_ids = [n.id for n in networks]
        task_props = {
            'ncontainer': ncontainer,
            'entrypoint': entrypoint,
            'env': env,
            'full_cores': [c.label for c in cores.get('full', [])],
            'part_cores': [c.label for c in cores.get('part', [])],
            'nshare': nshare,
            'networks': network_ids,
        }
        task = Task.create(type_, version, host, task_props)
        create_containers_with_macvlan.apply_async(
            args=(task.id, ncontainer, nshare, cores, network_ids),
            task_id='task:%d' % task.id
        )
        return task
    except Exception, e:
        logger.exception(e)
        host.release_cores(cores)
    return None

@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}
