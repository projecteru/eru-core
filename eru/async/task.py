#!/usr/bin/python
#coding:utf-8

import logging
from celery import current_app

from eru.common import code
from eru.common.clients import rds
from eru.async import dockerjob
from eru.utils.notify import TaskNotifier
from eru.models import Container, Task, Core, Port


logger = logging.getLogger(__name__)


@current_app.task()
def create_docker_container(task_id, ncontainer, core_ids, port_ids):
    """
    这个任务是在 host 上部署 ncontainer 个容器.
    可能占用 cores 这些核, 以及 ports 这些端口.
    """
    task = Task.get(task_id)
    notifier = TaskNotifier(task)
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
        notifier.pub_fail()
    else:
        for cid, cname, entrypoint, used_cores, expose_ports in containers:
            c = Container.create(cid, host, version, cname, entrypoint, used_cores, expose_ports)
            if c:
                # Notify agent update its status
                notifier.notify_agent(cid)
                rds.sadd('eru:agent:%s:containers' % host.name, cid)
                rds.hset('eru:app:%s:backends' % version.name, entrypoint, 'eru:app:entrypoint:%s:backends' % entrypoint)
                backends = ['%s:%s' % (host.ip, p.port) for p in expose_ports]
                rds.sadd('eru:app:entrypoint:%s:backends' % entrypoint, *backends)
        task.finish_with_result(code.TASK_SUCCESS)
        notifier.pub_success()


@current_app.task()
def build_docker_image(task_id, base):
    task = Task.get(task_id)
    notifier = TaskNotifier(task)
    try:
        repo, tag = base.split(':', 1)
        notifier.store_and_broadcast(dockerjob.pull_image(task.host, repo, tag))
        notifier.store_and_broadcast(dockerjob.build_image(task.host, task.version, base))
        notifier.store_and_broadcast(dockerjob.push_image(task.host, task.version))
        try:
            dockerjob.remove_image(task.version, task.host)
        except:
            pass
    except Exception, e:
        logger.exception(e)
        task.finish_with_result(code.TASK_FAILED)
        notifier.pub_fail()
    else:
        task.finish_with_result(code.TASK_SUCCESS)
        notifier.pub_success()
    finally:
        notifier.pub_build_finish()


@current_app.task()
def remove_containers(task_id, cids, rmi):
    task = Task.get(task_id)
    notifier = TaskNotifier(task)
    containers = Container.get_multi(cids)
    container_ids = [c.container_id for c in containers]
    host = task.host
    try:
        flags = {'eru:agent:%s:container:flag' % cid: 1 for cid in container_ids}
        rds.mset(**flags)
        dockerjob.remove_host_containers(containers, task.host)
        if rmi:
            dockerjob.remove_image(task.version, task.host)
    except Exception, e:
        logger.exception(e)
        task.finish_with_result(code.TASK_FAILED)
        notifier.pub_fail()
    else:
        for c in containers:
            backends = ['%s:%s' % (host.ip, p.port) for p in c.ports]
            entrypoint_backend_key = 'eru:app:entrypoint:%s:backends' % c.entrypoint
            rds.srem(entrypoint_backend_key, *backends)
            if not rds.scard(entrypoint_backend_key):
                rds.hdel('eru:app:%s:backends' % c.appname, c.entrypoint)
            c.delete()
        task.finish_with_result(code.TASK_SUCCESS)
        notifier.pub_success()
        rds.srem('eru:agent:%s:containers' % host.name, *container_ids)
        rds.delete(*flags.keys())

