# coding:utf-8
import logging
import time
from itertools import izip_longest

from celery import current_app
from more_itertools import chunked

from eru import consts
from eru.async import dockerjob
from eru.config import DOCKER_REGISTRY
from eru.helpers.check import wait_health_check
from eru.helpers.scheduler import average_schedule

from eru.ipam import ipam
from eru.models import Container, Task, Image
from eru.utils.notify import TaskNotifier
from eru.publish import (add_container_backends, remove_container_backends,
        add_container_for_agent, remove_container_for_agent,
        set_flag_for_agent, remove_flag_for_agent, publish_to_service_discovery)


_log = logging.getLogger(__name__)


@current_app.task()
def build_docker_image(task_id, base, file_path):
    task = Task.get(task_id)
    if not task:
        _log.error('Task (id=%s) not found, quit', task_id)
        return

    _log.info('Task<id=%s>: Start on host %s', task_id, task.host.ip)
    notifier = TaskNotifier(task)

    app = task.app
    host = task.host
    version = task.version

    try:
        repo, tag = base.split(':', 1)
        _log.info('Task<id=%s>: Pull base image (base=%s)', task_id, base)
        notifier.store_and_broadcast(dockerjob.pull_image(host, repo, tag))

        _log.info('Task<id=%s>: Build image (base=%s)', task_id, base)
        notifier.store_and_broadcast(dockerjob.build_image(host, version, base, file_path))

        _log.info('Task<id=%s>: Push image (base=%s)', task_id, base)
        last_line = notifier.store_and_broadcast(dockerjob.push_image(host, version))
        dockerjob.remove_image(version, host)
    except Exception, e:
        task.finish(consts.TASK_FAILED)
        task.reason = str(e.message)
        notifier.pub_fail()
        _log.error('Task<id=%s>, exception', task_id)
        _log.exception(e)
    else:
        # 粗暴的判断, 如果推送成功说明build成功
        if 'digest: sha256' in last_line.lower():
            task.finish(consts.TASK_SUCCESS)
            task.reason = 'ok'

            image_url = '%s/%s:%s' % (DOCKER_REGISTRY, app.name, version.short_sha)
            Image.create(app.id, version.id, image_url)

            notifier.pub_success()
        else:
            task.finish(consts.TASK_FAILED)
            task.reason = 'failed to push image to image hub'
            notifier.pub_fail()
        _log.info('Task<id=%s>: Done', task_id)
    finally:
        notifier.pub_build_finish()


@current_app.task()
def remove_containers(task_id, cids, rmi=False):
    task = Task.get(task_id)
    if not task:
        _log.error('Task (id=%s) not found, quit', task_id)
        return

    _log.info('Task<id=%s>: Start on host %s', task_id, task.host.ip)
    notifier = TaskNotifier(task)

    containers = Container.get_multi(cids)
    if not containers:
        _log.error('Task (id=%s) no container found, quit')
        return

    for c in containers:
        c.in_removal = 1

    container_ids = [c.container_id for c in containers if c]
    host = task.host
    try:
        set_flag_for_agent(container_ids)
        for c in containers:
            remove_container_backends(c)
            _log.info('Task<id=%s>: Container (cid=%s) backends removed', task_id, c.short_id)

        appnames = {c.appname for c in containers}
        publish_to_service_discovery(*appnames)

        time.sleep(3)

        dockerjob.remove_host_containers(containers, host)
        _log.info('Task<id=%s>: Containers (cids=%s) removed', task_id, cids)

        if rmi:
            try:
                dockerjob.remove_image(task.version, host)
            except Exception as e:
                _log.error('Task<id=%s>, fail to remove image', task_id, e)
    except Exception as e:
        task.finish(consts.TASK_FAILED)
        task.reason = str(e.message)
        notifier.pub_fail()
        _log.error('Task<id=%s> exception', task_id)
        _log.exception(e)
    else:
        for c in containers:
            c.delete()
        task.finish(consts.TASK_SUCCESS)
        task.reason = 'ok'
        notifier.pub_success()
        remove_container_for_agent(host, container_ids)
        remove_flag_for_agent(container_ids)
        _log.info('Task<id=%s>: Done', task_id)


def _iter_cores(cores, ncontainer):
    full_cores, part_cores = cores.get('full', []), cores.get('part', [])
    if not (full_cores or part_cores):
        return (([], []) for _ in range(ncontainer))

    return izip_longest(
        chunked(full_cores, len(full_cores)/ncontainer),
        chunked(part_cores, len(part_cores)/ncontainer),
        fillvalue=[]
    )


def _clean_failed_containers(cid):
    # 清理掉失败的容器, 释放核, 释放ip
    _log.info('Cleaning failed container (cid=%s)', cid)
    container = Container.get_by_container_id(cid)
    if not container:
        return

    dockerjob.remove_container_by_cid([cid], container.host)
    container.delete()


@current_app.task()
def create_containers(task_id, ncontainer, nshare, cores, network_ids, spec_ips=None):
    """
    执行task_id的任务. 部署ncontainer个容器, 占用*_core_ids这些核, 绑定到networks这些子网
    """
    _log.info('Task<id=%s>: Started', task_id)
    task = Task.get(task_id)
    if not task:
        _log.error('Task (id=%s) not found, quit', task_id)
        return

    if spec_ips is None:
        spec_ips = []

    need_network = bool(network_ids)
    networks = [ipam.get_pool(n) for n in network_ids]

    notifier = TaskNotifier(task)
    host = task.host
    version = task.version
    entrypoint = task.props['entrypoint']
    env = task.props['env']
    ports = task.props['ports']
    args = task.props['args']
    # use raw
    image = task.props['image']
    callback_url = task.props['callback_url']
    cpu_shares = int(float(nshare) / host.pod.core_share * 1024) if nshare else 1024

    cids = []
    backends = []
    entry = version.appconfig.entrypoints[entrypoint]

    for fcores, pcores in _iter_cores(cores, ncontainer):
        cores_for_one_container = {'full': fcores, 'part': pcores}
        # 在宿主机上创建容器
        try:
            cid, cname = dockerjob.create_one_container(host, version,
                entrypoint, env, fcores+pcores, ports=ports, args=args,
                cpu_shares=cpu_shares, image=image, need_network=need_network)
        except Exception as e:
            # 写给celery日志看
            _log.exception(e)
            host.release_cores(cores_for_one_container, nshare)
            continue

        # 容器记录下来
        c = Container.create(cid, host, version, cname, entrypoint, cores_for_one_container, env, nshare, callback_url)

        # 为容器创建网络栈
        # 同时把各种信息都记录下来
        # 如果失败, 清除掉所有记录和宿主机上的容器
        # 循环下一次尝试
        cidrs = [n.netspace for n in networks]
        if not ipam.allocate_ips(cidrs, cid, spec_ips):
            _clean_failed_containers(cid)
            continue

        notifier.notify_agent(c)
        add_container_for_agent(host, c)
        add_container_backends(c)
        cids.append(cid)
        backends.extend(c.get_backends())

        c.callback_report(status='start')

    health_check = entry.get('health_check', '')
    if health_check and backends:
        urls = [b + health_check for b in backends]
        if not wait_health_check(urls):
            # TODO 这里要么回滚要么报警
            _log.info('Task<id=%s>: Done, but something went error', task_id)
            return

    publish_to_service_discovery(version.name)
    task.finish(consts.TASK_SUCCESS)
    task.reason = 'ok'
    task.container_ids = cids
    notifier.pub_success()

    _log.info('Task<id=%s>: Done', task_id)


@current_app.task()
def migrate_container(container_id, need_to_remove=True):
    container = Container.get_by_container_id(container_id)
    if not container:
        _log.error('container %s is not found, ignore migration', container_id)
        return

    ncore, nshare= container.pod.get_core_allocation(container.ncore)
    host_cores = average_schedule(container.host.pod, 1, ncore, nshare, None)
    if not host_cores:
        _log.error('not enough cores to migrate')
        return

    cids = [container.id]
    spec_ips = cidrs = container.get_ips()
    (host, container_count), cores = next(host_cores.iteritems())

    props = {
        'ncontainer': 1,
        'entrypoint': container.entrypoint,
        'env': container.env,
        'full_cores': [c.label for c in cores.get('full', [])],
        'part_cores': [c.label for c in cores.get('part', [])],
        'ports': None,
        'args': None,
        'nshare': nshare,
        'networks': cidrs,
        'image': None,
        'route': '',
        'callback_url': container.callback_url,
        'container_ids': cids,
    }
    task = Task.create(consts.TASK_MIGRATE, container.version, host, props)
    if not task:
        _log.error('create migrate task error')
        return

    _log.info('start migration...')
    if need_to_remove:
        remove_containers.apply(args=(task.id, cids, False), task_id='task:%s' % task.id)
    create_containers.apply(args=(task.id, 1, nshare, cores, cidrs, spec_ips), task_id='task:%s' % task.id)
    _log.info('migration done')
