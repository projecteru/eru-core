#!/usr/bin/python
#coding:utf-8

import logging
from celery import current_app

from eru.common import code
from eru.async import dockerjob
from eru.models import Container, Task, Core, Port


logger = logging.getLogger(__name__)


@current_app.task()
def create_docker_container(task_id, ncontainer, core_ids, port_ids):
    """
    这个任务是在 host 上部署 ncontainer 个容器.
    可能占用 cores 这些核, 以及 ports 这些端口.
    """
    task = Task.get(task_id)
    cores = Core.get_multi(core_ids)
    ports = Port.get_multi(port_ids)
    try:
        host = task.host
        version = task.version
        entrypoint = task.props['entrypoint']
        env = task.props['env']
        containers = dockerjob.create_containers(host, version,
                entrypoint, env, ncontainer, cores, ports)
    except Exception, e:
        logger.exception(e)
        host.release_cores(cores)
        host.release_ports(ports)
        task.finish_with_result(code.TASK_FAILED)
    else:
        for cid, cname, entrypoint, used_cores, port in containers:
            Container.create(cid, host, version, cname, entrypoint, used_cores, port)

        task.finish_with_result(code.TASK_SUCCESS)


@current_app.task()
def build_docker_image(task_id, base):
    task = Task.get(task_id)
    try:
        for line in dockerjob.build_image(task.host, task.version, base):
            print line
    except Exception, e:
        logger.exception(e)
        task.finish_with_result(code.TASK_FAILED)
    else:
        task.finish_with_result(code.TASK_SUCCESS)

