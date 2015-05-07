#!/usr/bin/python
#coding:utf-8

import logging
import more_itertools
from celery import current_app

from eru.common import code
from eru.common.clients import rds
from eru.async import dockerjob
from eru.utils.notify import TaskNotifier
from eru.models import Container, Task, Core, Network

logger = logging.getLogger(__name__)

def add_container_backends(container):
    """单个container所拥有的后端服务
    HKEYS app_key 可以知道有哪些后端
    HGET 上面的结果可以知道后端都从哪里拿
    SMEMBERS entrypoint_key 可以拿出所有的后端
    """
    app_key = 'eru:app:{0}:backends'.format(container.appname)
    entrypoint_key = 'eru:app:{0}:entrypoint:{1}:backends'.format(container.appname, container.entrypoint)
    rds.hset(app_key, container.entrypoint, entrypoint_key)

    backends = container.get_backends()
    if backends:
        rds.sadd(entrypoint_key, *backends)

def remove_container_backends(container):
    """删除单个container的后端服务
    并不删除有哪些entrypoint, 这些service discovery方便知道哪些没了"""
    entrypoint_key = 'eru:app:{0}:entrypoint:{1}:backends'.format(container.appname, container.entrypoint)
    backends = container.get_backends()
    if backends:
        rds.srem(entrypoint_key, *backends)

def add_container_for_agent(container):
    """agent需要从key里取值出来去跟踪
    SMEMBERS key 可以拿出这个host上所有的container"""
    host = container.host
    key = 'eru:agent:{0}:containers'.format(host.name)
    rds.sadd(key, container.container_id)

def remove_container_for_agent(container):
    host = container.host
    key = 'eru:agent:{0}:containers'.format(host.name)
    rds.srem(key, container.container_id)

def publish_to_service_discovery(*appnames):
    for appname in appnames:
        rds.publish('eru:discovery:published', appname)

def dont_report_these(container_ids):
    """告诉agent这些不要care了"""
    flags = {'eru:agent:%s:container:flag' % cid: 1 for cid in container_ids}
    rds.mset(**flags)

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
        for c in containers:
            remove_container_backends(c)
        appnames = {c.appname for c in containers}
        publish_to_service_discovery(*appnames)

        dockerjob.remove_host_containers(containers, host)
        if rmi:
            dockerjob.remove_image(task.version, host)
    except Exception, e:
        logger.exception(e)
        task.finish_with_result(code.TASK_FAILED)
        notifier.pub_fail()
    else:
        for c in containers:
            c.delete()
        task.finish_with_result(code.TASK_SUCCESS)
        notifier.pub_success()
        if container_ids:
            rds.srem('eru:agent:%s:containers' % host.name, *container_ids)
        rds.delete(*flags.keys())

@current_app.task()
def create_containers_with_macvlan(task_id, ncontainer, core_ids, network_ids):
    """
    执行task_id的任务. 部署ncontainer个容器, 占用core_ids这些核, 绑定到networks这些子网
    """
    task = Task.get(task_id)
    if not task:
        return

    networks = Network.get_multi(network_ids)

    notifier = TaskNotifier(task)
    host = task.host
    version = task.version
    entrypoint = task.props['entrypoint']
    env = task.props['env']
    used_cores = Core.get_multi(core_ids)

    pub_agent_vlan_key = 'eru:agent:%s:vlan' % host.name
    feedback_key = 'eru:agent:%s:feedback' % task_id

    cids = []

    for cores in more_itertools.chunked(used_cores, len(core_ids)/ncontainer):
        try:
            cid, cname = dockerjob.create_one_container(host, version,
                    entrypoint, env, cores)
        except:
            host.release_cores(cores)
            continue

        ips = [n.acquire_ip() for n in networks]
        ip_dict = {ip.vlan_address: ip for ip in ips}

        if ips:
            ident_id = cname.split('_')[-1]
            values = [str(task_id), cid, ident_id] + ['{0}:{1}'.format(ip.vlan_seq_id, ip.vlan_address) for ip in ips]
            rds.publish(pub_agent_vlan_key, '|'.join(values))

        for _ in ips:
            # timeout 15s
            rv = rds.blpop(feedback_key, 15)
            if rv is None:
                break
            # rv is like (feedback_key, 'succ|container_id|vethname|ip')
            succ, _, vethname, vlan_address = rv[1].split('|')
            if succ == '0':
                break
            ip = ip_dict.get(vlan_address, None)
            if ip:
                ip.set_vethname(vethname)

        else:
            logger.info('Creating container with cid %s and ips %s' % (cid, ips))
            c = Container.create(cid, host, version, cname, entrypoint, cores, env)
            for ip in ips:
                ip.assigned_to_container(c)
            notifier.notify_agent(cid)
            add_container_for_agent(c)
            add_container_backends(c)
            cids.append(cid)
            # 略过清理工作
            continue

        # 清理掉失败的容器, 释放核, 释放ip
        logger.info('Cleaning failed container with cid %s' % cid)
        dockerjob.remove_container_by_cid([cid], host)
        host.release_cores(cores)
        [ip.release() for ip in ips]
        # 失败了就得清理掉这个key
        rds.delete(feedback_key)

    publish_to_service_discovery(version.name)
    task.finish_with_result(code.TASK_SUCCESS, container_ids=cids)
    notifier.pub_success()
