#!/usr/bin/python
#coding:utf-8

import logging

from threading import RLock
from collections import defaultdict
from flask import Blueprint, request, jsonify, abort
from celery import current_app

from eru.common import code
from eru.queries import group, host, app, task

deploy = Blueprint('deploy', __name__, url_prefix='/deploy')

#TODO only work in single process env
RESLOCK = defaultdict(RLock)

logger = logging.getLogger(__name__)

@deploy.route('/')
def index():
    return 'deploy control'

@deploy.route('/create/<group_name>/<pod_name>/<appname>', methods=['PUT', ])
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
    expose = bool(data['expose'])

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
                ports = host.get_host_ports(expose, *k)
                tasks_info.append((application, version, k[0], k[1], cpus, ports))
                host.use_cpus(cpus)
                host.use_ports(ports)
        except Exception:
            abort(code.HTTP_BAD_REQUEST)

    ts = []
    for task_info in tasks_info:
        #task_info contain (application, version, host, num, cpus, ports)
        #create_task will always correct
        t = _create_task(*task_info)
        if not t:
            #TODO need response
            logger.error(application.name, version.sha, task_info[2].addr)
            _release_cpus_ports(task_info[4], task_info[5])
            continue
        ts.append(t.id)
        #TODO threading spawn
        _create_container.delay(t, task_info[4], task_info[5])

    return jsonify(msg=code.OK, tasks=ts), code.HTTP_CREATED

def _release_cpus_ports(cpus, ports):
    if cpus:
        host.release_cpus(cpus)
    if ports:
        host.release_ports(ports)

def _create_task(application, version, host, num, cpus, ports):
    try:
        return task.create_task(code.TASK_CREATE, application, version, host)
    except Exception, e:
        logger.exception(e)
    return None

@current_app.task(bind=True)
def _create_container(self, t, cpus, ports):
    #TODO get docker deploy status
    print self
    try:
        # if suceess
        import time
        time.sleep(60)
    except Exception, e:
        logger.exception(e)
        _release_cpus_ports(cpus, ports)
        task.done(t, code.TASK_FAILED)
    else:
        task.done(t, code.TASK_SUCCESS)
    # container.create()

