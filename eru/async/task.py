#!/usr/bin/python
#coding:utf-8

import logging
from celery import current_app

from eru.common import code
from eru.common.clients import rds
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
        containers = dockerjob.create_containers(
            host, version, entrypoint,
            env, ncontainer, cores, ports
        )
    except Exception, e:
        logger.exception(e)
        host.release_cores(cores)
        host.release_ports(ports)
        task.finish_with_result(code.TASK_FAILED)
        rds.publish(task.result_key, 'fail')
    else:
        for cid, cname, entrypoint, used_cores, expose_ports in containers:
            Container.create(cid, host, version, cname, entrypoint, used_cores, expose_ports)

        task.finish_with_result(code.TASK_SUCCESS)
        rds.publish(task.result_key, 'success')


@current_app.task()
def build_docker_image(task_id, base):
    task = Task.get(task_id)
    try:
        repo, tag = base.split(':', 1)
        for line in dockerjob.pull_image(task.host, repo, tag):
            rds.rpush(task.log_key, line)
            rds.publish(task.publish_key, line)
        for line in dockerjob.build_image(task.host, task.version, base):
            rds.rpush(task.log_key, line)
            rds.publish(task.publish_key, line)
        for line in dockerjob.push_image(task.host, task.version):
            rds.rpush(task.log_key, line)
            rds.publish(task.publish_key, line)
        dockerjob.remove_image(task.version, task.host)
        rds.publish(task.publish_key, code.PUB_END_MESSAGE)
    except Exception, e:
        logger.exception(e)
        task.finish_with_result(code.TASK_FAILED)
        rds.publish(task.result_key, 'fail')
    else:
        task.finish_with_result(code.TASK_SUCCESS)
        rds.publish(task.result_key, 'success')


@current_app.task()
def remove_containers(task_id, cids, rmi):
    task = Task.get(task_id)
    containers = Container.get_multi(cids)
    try:
        dockerjob.remove_host_containers(containers, task.host)
        if rmi:
            dockerjob.remove_image(task.version, task.host)
    except Exception, e:
        logger.exception(e)
        task.finish_with_result(code.TASK_FAILED)
        rds.publish(task.result_key, 'fail')
    else:
        for c in containers:
            c.delete()
        task.finish_with_result(code.TASK_SUCCESS)
        rds.publish(task.result_key, 'success')

