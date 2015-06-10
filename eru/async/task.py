#!/usr/bin/python
#coding:utf-8

from more_itertools import chunked
from itertools import izip_longest
from celery import current_app
from flask import current_app as current_flask

from eru.common import code
from eru.common.clients import rds
from eru.async import dockerjob
from eru.utils.notify import TaskNotifier
from eru.models import Container, Task, Network

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
    current_flask.logger.info('Task<id=%s>: Started', task_id)
    task = Task.get(task_id)
    if not task:
        current_flask.logger.error('Task (id=%s) not found, quit', task_id)
        return

    notifier = TaskNotifier(task)
    try:
        repo, tag = base.split(':', 1)
        current_flask.logger.info('Task<id=%s>: Pull base image (base=%s)', task_id, base)
        notifier.store_and_broadcast(dockerjob.pull_image(task.host, repo, tag))
        current_flask.logger.info('Task<id=%s>: Build image (base=%s)', task_id, base)
        notifier.store_and_broadcast(dockerjob.build_image(task.host, task.version, base))
        current_flask.logger.info('Task<id=%s>: Push image (base=%s)', task_id, base)
        notifier.store_and_broadcast(dockerjob.push_image(task.host, task.version))
        dockerjob.remove_image(task.version, task.host)
    except Exception, e:
        task.finish_with_result(code.TASK_FAILED)
        notifier.pub_fail()
        current_flask.logger.error('Task<id=%s>: Exception (e=%s)', task_id, e)
    else:
        task.finish_with_result(code.TASK_SUCCESS)
        notifier.pub_success()
        current_flask.logger.info('Task<id=%s>: Done', task_id)
    finally:
        notifier.pub_build_finish()

@current_app.task()
def remove_containers(task_id, cids, rmi=False):
    current_flask.logger.info('Task<id=%s>: Started', task_id)
    task = Task.get(task_id)
    if not task:
        current_flask.logger.error('Task (id=%s) not found, quit', task_id)
        return

    notifier = TaskNotifier(task)
    containers = Container.get_multi(cids)
    container_ids = [c.container_id for c in containers]
    host = task.host
    try:
        flags = {'eru:agent:%s:container:flag' % cid: 1 for cid in container_ids}
        rds.mset(**flags)
        for c in containers:
            remove_container_backends(c)
            current_flask.logger.info('Task<id=%s>: Container (cid=%s) backends removed',
                    task_id, c.container_id[:7])
        appnames = {c.appname for c in containers}
        publish_to_service_discovery(*appnames)

        dockerjob.remove_host_containers(containers, host)
        current_flask.logger.info('Task<id=%s>: Containers (cids=%s) removed', task_id, cids)
        if rmi:
            dockerjob.remove_image(task.version, host)
    except Exception, e:
        task.finish_with_result(code.TASK_FAILED)
        notifier.pub_fail()
        current_flask.logger.error('Task<id=%s>: Exception (e=%s)', task_id, e)
    else:
        for c in containers:
            c.delete()
        task.finish_with_result(code.TASK_SUCCESS)
        notifier.pub_success()
        if container_ids:
            rds.srem('eru:agent:%s:containers' % host.name, *container_ids)
        rds.delete(*flags.keys())
        current_flask.logger.info('Task<id=%s>: Done', task_id)

@current_app.task()
def create_containers_with_macvlan(task_id, ncontainer, nshare, cores, network_ids):
    """
    执行task_id的任务. 部署ncontainer个容器, 占用*_core_ids这些核, 绑定到networks这些子网
    """
    #TODO support part core
    current_flask.logger.info('Task<id=%s>: Started', task_id)
    task = Task.get(task_id)
    if not task:
        current_flask.logger.error('Task (id=%s) not found, quit', task_id)
        return

    networks = Network.get_multi(network_ids)

    notifier = TaskNotifier(task)
    host = task.host
    version = task.version
    entrypoint = task.props['entrypoint']
    env = task.props['env']
    # use raw
    image = task.props['image']
    cpu_shares = int(float(nshare) / host.pod.core_share * 1024) if nshare else 1024

    pub_agent_vlan_key = 'eru:agent:%s:vlan' % host.name
    feedback_key = 'eru:agent:%s:feedback' % task_id

    cids = []

    full_cores, part_cores = cores.get('full', []), cores.get('part', [])
    for fcores, pcores in izip_longest(
        chunked(full_cores, len(full_cores)/ncontainer),
        chunked(part_cores, len(part_cores)/ncontainer),
        fillvalue=[]
    ):
        cores_for_one_container = {'full': fcores, 'part': pcores}
        try:
            cid, cname = dockerjob.create_one_container(host, version,
                entrypoint, env, fcores+pcores, cpu_shares, image=image)
        except:
            host.release_cores(cores_for_one_container, nshare)
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
            current_flask.logger.info('Creating container (cid=%s, ips=%s)', cid, ips)
            c = Container.create(cid, host, version, cname, entrypoint, cores_for_one_container, env, nshare)
            for ip in ips:
                ip.assigned_to_container(c)
            notifier.notify_agent(cid)
            add_container_for_agent(c)
            add_container_backends(c)
            cids.append(cid)
            # 略过清理工作
            continue

        # 清理掉失败的容器, 释放核, 释放ip
        current_flask.logger.info('Cleaning failed container (cid=%s)', cid)
        dockerjob.remove_container_by_cid([cid], host)
        host.release_cores(cores_for_one_container, nshare)
        [ip.release() for ip in ips]
        # 失败了就得清理掉这个key
        rds.delete(feedback_key)

    publish_to_service_discovery(version.name)
    task.finish_with_result(code.TASK_SUCCESS, container_ids=cids)
    notifier.pub_success()
    current_flask.logger.info('Task<id=%s>: Done', task_id)
