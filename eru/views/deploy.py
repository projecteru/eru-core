#!/usr/bin/python
#coding:utf-8

import logging

from threading import RLock
from collections import defaultdict
from flask import Blueprint, request, jsonify, abort

from eru.async.task import create_container
from eru.common import code
from eru.models import App, Group, Pod, Task
from eru.utils.views import check_request_json

bp = Blueprint('deploy', __name__, url_prefix='/api/deploy')

#TODO only work in single process env
RESLOCK = defaultdict(RLock)

logger = logging.getLogger(__name__)


@bp.route('/')
def index():
    return 'deploy control'


@bp.route('/private/<group_name>/<pod_name>/<appname>', methods=['PUT', ])
@check_request_json(['ncore', 'ncontainer', 'version', 'entrypoint', 'env'], code.HTTP_BAD_REQUEST)
def create_private(group_name, pod_name, appname):
    '''
       ncore: int cpu num per container -1 means share
       ncontainer: int container nums
       version: string deploy version
       expose: bool true or false, default true
    '''
    data = request.get_json()

    application = App.get_by_name(appname)
    if not application:
        abort(code.HTTP_BAD_REQUEST)
    version = application.get_version(data['version'])
    if not version:
        abort(code.HTTP_BAD_REQUEST)
    group = Group.get_by_name(group_name)
    if not group:
        abort(code.HTTP_BAD_REQUEST)
    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(code.HTTP_BAD_REQUEST)

    # TODO check if group has this pod

    ncore = int(data['ncore']) # 是说一个容器要几个核...
    ncontainer = int(data['ncontainer'])
    expose = bool(data.get('expose', 'true'))

    tasks_info = []
    with RESLOCK['%s:%s' % (group_name, pod_name)]:
        # check if task need cpus more than free cpus
        if ncore > 0 and group.get_max_containers(pod, ncore) < ncontainer:
            abort(code.HTTP_BAD_REQUEST)

        try:
            host_cores = group.get_free_cores(pod, ncontainer, ncore)
            if not host_cores:
                # ......
                abort(code.HTTP_BAD_REQUEST)
            # 无穷无尽的奇怪感
            for (host, container_count), cores in host_cores.iteritems():
                ports = host.get_free_ports(container_count) if expose else []
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

    return jsonify(msg=code.OK, tasks=ts), code.HTTP_CREATED


@bp.route('/public/<group_name>/<pod_name>/<appname>', methods=['PUT', ])
@check_request_json(['type', 'ncontainer', 'version'], code.HTTP_BAD_REQUEST)
def create_public(group_name, pod_name, appname):
    '''
       ncontainer: int container nums
       version: string deploy version
       expose: bool true or false, default true
       type: 1, 2, 3, default 1, create/test/build
    '''
    data = request.get_json()

    application = App.get_by_name(appname)
    if not application:
        abort(code.HTTP_BAD_REQUEST)
    version = application.get_version(data['version'])
    if not version:
        abort(code.HTTP_BAD_REQUEST)
    group = Group.get_by_name(group_name)
    if not group:
        abort(code.HTTP_BAD_REQUEST)
    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(code.HTTP_BAD_REQUEST)

    typ = int(data['type'])
    ncontainer = int(data['ncontainer'])
    expose = bool(data.get('expose', 'true'))
    #ignore test and build container
    if typ in [2, 3]:
        expose = False

    tasks_info = []
    with RESLOCK['%s:%s' % (group_name, pod_name)]:
        try:
            # TODO 这里是轮询? 尽可能均匀部署对吧?
            for host in pod.get_free_public_hosts(ncontainer):
                ports = host.get_free_ports(1) if expose else []
                tasks_info.append((version, host, 1, [], ports))
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

    return jsonify(msg=code.OK, tasks=ts), code.HTTP_CREATED


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
        create_container.apply_async(
            args=(task, ncontainer, cores, ports),
            task_id='task:%d' % task.id
        )
        return task
    except Exception, e:
        logger.exception(e)
        host.release_ports(ports)
        host.release_cores(cores)
    return None

