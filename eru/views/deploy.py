#!/usr/bin/python
#coding:utf-8

import logging

from threading import RLock
from collections import defaultdict
from flask import Blueprint, request, jsonify, abort

from eru.async.task import create_container
from eru.common import code
from eru.queries import group, host, app, task

deploy = Blueprint('deploy', __name__, url_prefix='/deploy')

#TODO only work in single process env
RESLOCK = defaultdict(RLock)

logger = logging.getLogger(__name__)

@deploy.route('/')
def index():
    return 'deploy control'

@deploy.route('/private/<group_name>/<pod_name>/<appname>', methods=['PUT', ])
def create_private(group_name, pod_name, appname):
    '''
       ncpu: int cpu num per container -1 means share
       ncontainer: int container nums
       version: string deploy version
       expose: bool true or false, default true
    '''
    data = request.get_json()
    if not data or not data.get('ncpu', None) or \
        not data.get('ncontainer', None) or \
        not data.get('version', None):
        abort(code.HTTP_BAD_REQUEST)

    application = app.get_app(appname)
    if not application:
        abort(code.HTTP_BAD_REQUEST)
    version = app.get_version(data['version'], application)
    if not version:
        abort(code.HTTP_BAD_REQUEST)

    ncpu = int(data['ncpu'])
    ncontainer = int(data['ncontainer'])
    expose = bool(data.get('expose', 'true'))

    tasks_info = []
    with RESLOCK['%s:%s' % (group_name, pod_name)]:
        # check if task need cpus more than free cpus
        if ncpu > 0 and group.get_group_max_containers(group_name, ncpu) < ncontainer:
            abort(code.HTTP_BAD_REQUEST)

        try:
            host_cpus = host.get_host_cpus(group_name, pod_name, ncpu, ncontainer)
            if not host_cpus:
                abort(code.HTTP_BAD_REQUEST)
            for k, cpus in host_cpus.iteritems():
                ports = host.get_host_ports(*k) if expose else []
                tasks_info.append((application, version, k[0], k[1], cpus, ports))
                host.use_cpus(cpus)
                host.use_ports(ports)
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

@deploy.route('/public/<group_name>/<pod_name>/<appname>', methods=['PUT', ])
def create_public(group_name, pod_name, appname):
    '''
       ncontainer: int container nums
       version: string deploy version
       expose: bool true or false, default true
       type: 1, 2, 3, default 1, create/test/build
    '''
    data = request.get_json()
    if not data or not data.get('type', None) or \
        not data.get('ncontainer', None) or \
        not data.get('version', None):
        abort(code.HTTP_BAD_REQUEST)

    application = app.get_app(appname)
    if not application:
        abort(code.HTTP_BAD_REQUEST)
    version = app.get_version(data['version'], application)
    if not version:
        abort(code.HTTP_BAD_REQUEST)
    if not group.get_group_pod(group_name, pod_name):
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
            for h in host.get_free_host(pod_name, ncontainer):
                port = host.get_host_ports(h, 1) if expose else []
                tasks_info.append((application, version, h, 1, [], port))
                host.use_ports(port)
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

def _create_task(typ, application, version, host, num, cpus, ports):
    try:
        t = task.create_task(typ, application, version, host)
        create_container.apply_async(
                args=(t, cpus, ports),
                task_id='task:%d' % t.id
        )
        return t
    except Exception, e:
        logger.exception(e)
        task.release_cpus_ports(cpus, ports)
    return None

