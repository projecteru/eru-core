#!/usr/bin/python
#coding:utf-8

import logging

from flask import Blueprint, request, abort

from eru.async.task import create_docker_container, build_docker_image
from eru.common import code
from eru.common.clients import rds
from eru.models import App, Group, Pod, Task
from eru.utils.views import check_request_json, jsonify


bp = Blueprint('deploy', __name__, url_prefix='/api/deploy')
logger = logging.getLogger(__name__)


@bp.route('/')
def index():
    return 'deploy control'


@bp.route('/private/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['ncore', 'ncontainer', 'version', 'entrypoint', 'env'])
@jsonify
def create_private(group_name, pod_name, appname):
    """
    ncore: int cpu num per container -1 means share
    ncontainer: int container nums
    version: string deploy version
    expose: bool true or false, default true
    """
    data = request.get_json()
    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])

    # TODO check if group has this pod

    ncore = int(data['ncore']) # 是说一个容器要几个核...
    ncontainer = int(data['ncontainer'])
    appconfig = version.appconfig
    entry = appconfig.entrypoints[data['entrypoint']]

    tasks_info = []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        # 不够了
        if ncore > 0 and group.get_max_containers(pod, ncore) < ncontainer:
            abort(code.HTTP_BAD_REQUEST)

        try:
            host_cores = group.get_free_cores(pod, ncontainer, ncore)
            # 这个pod都不够host了
            if not host_cores:
                abort(code.HTTP_BAD_REQUEST)

            for (host, container_count), cores in host_cores.iteritems():
                ports = host.get_free_ports(container_count) if entry.get('port') else []
                tasks_info.append(
                    (version, host, container_count, cores, ports, data['entrypoint'], data['env'])
                )
                host.occupy_cores(cores)
                host.occupy_ports(ports)
        except Exception, e:
            logger.exception(e)
            abort(code.HTTP_BAD_REQUEST)

    ts = []
    for task_info in tasks_info:
        #task_info contain (application, version, host, num, cpus, ports)
        #create_task will always correct
        t = _create_task(code.TASK_CREATE, *task_info)
        if not t:
            continue
        ts.append(t.id)

    return {'r': 0, 'msg': 'ok', 'tasks': ts}


@bp.route('/public/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['ncontainer', 'version', 'entrypoint', 'env'])
@jsonify
def create_public(group_name, pod_name, appname):
    """
    ncontainer: int container nums
    version: string deploy version
    expose: bool true or false, default true
    """
    data = request.get_json()

    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])

    ncontainer = int(data['ncontainer'])
    appconfig = version.appconfig
    entry = appconfig['entrypoints'][data['entrypoint']]

    tasks_info = []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        try:
            # TODO 这里是轮询? 尽可能均匀部署对吧?
            for host in pod.get_free_public_hosts(ncontainer):
                ports = host.get_free_ports(1) if entry.get('port') else []
                tasks_info.append(
                    (version, host, 1, [], ports, data['entrypoint'], data['env'])
                )
                host.occupy_ports(ports)
        except Exception, e:
            logger.exception(e)
            abort(code.HTTP_BAD_REQUEST)

    ts = []
    for task_info in tasks_info:
        #task_info contain (version, host, num, cpus, ports)
        #create_task will always correct
        t = _create_task(code.TASK_CREATE, *task_info)
        if not t:
            continue
        ts.append(t.id)

    return {'r':0, 'msg': 'ok', 'tasks': ts}


@bp.route('/build/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['base', 'version'])
@jsonify
def build_image(group_name, pod_name, appname):
    data = request.get_json()
    group, pod, application, version = validate_instance(group_name,
            pod_name, appname, data['version'])
    # TODO
    # 这个group可以用这个pod不?
    # 这个group可以build这个version不?
    base = data['base']
    host = pod.get_free_public_hosts(1)[0]
    try:
        task_props = {'base': base}
        task = Task.create(code.TASK_BUILD, version, host, task_props)
        build_docker_image.apply_async(
            args=(task, base),
            task_id='task:%d' % task.id
        )
        return {'r': 0, 'msg': 'ok', 'task': task.id}
    except Exception, e:
        logger.exception(e)
        return {'r': 1, 'msg': str(e), 'task': None}


def validate_instance(group_name, pod_name, appname, version):
    group = Group.get_by_name(group_name)
    if not group:
        abort(code.HTTP_BAD_REQUEST)

    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(code.HTTP_BAD_REQUEST)

    application = App.get_by_name(appname)
    if not application:
        abort(code.HTTP_BAD_REQUEST)

    version = application.get_version(version)
    if not version:
        abort(code.HTTP_BAD_REQUEST)

    return group, pod, application, version


def _create_task(type_, version, host, ncontainer, cores, ports, entrypoint, env):
    try:
        task_props = {
            'ncontainer': ncontainer,
            'entrypoint': entrypoint,
            'env': env,
            'cores': [c.id for c in cores],
            'ports': [p.id for p in ports],
        }
        task = Task.create(type_, version, host, task_props)
        create_docker_container.apply_async(
            args=(task, ncontainer, cores, ports),
            task_id='task:%d' % task.id
        )
        return task
    except Exception, e:
        logger.exception(e)
        host.release_ports(ports)
        host.release_cores(cores)
    return None

