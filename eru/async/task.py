#!/usr/bin/python
#coding:utf-8

import logging
from celery import current_app

from eru.common import code
from eru.async import dockerjob

logger = logging.getLogger(__name__)

@current_app.task()
def create_container(task, ncontainer, cores, ports):
    """
    这个任务是在 host 上部署 ncontainer 个容器.
    可能占用 cores 这些核, 以及 ports 这些端口.
    """
    try:
        host = task.host
        version = task.version
        entrypoint = 'web' # TODO 这里得拿出来
        container_ids = dockerjob.create_containers(host, version,
                entrypoint, '', ncontainer, cores, ports)
    except Exception, e:
        logger.exception(e)
        host.release_cores(cores)
        host.release_ports(ports)
        task.finish_with_result(code.TASK_FAILED)
    else:
        task.finish_with_result(code.TASK_SUCCESS)
    # container.create()

