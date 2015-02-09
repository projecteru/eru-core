#!/usr/bin/python
#coding:utf-8

import logging
from celery import current_app

from eru.common import code
from eru.queries import task
from eru.async.dockerjob import create_container

logger = logging.getLogger(__name__)

@current_app.task()
def create_container(t, cpus, port):
    #TODO get docker deploy status
    try:
        host = t.host().addr
        version = t.version()
        sub = 'web' # TODO 这里得拿出来
        create_container(host, version, sub, port.port)
    except Exception, e:
        logger.exception(e)
        task.release_cpus_ports(cpus, port)
        task.done(t, code.TASK_FAILED)
    else:
        task.done(t, code.TASK_SUCCESS)
    # container.create()

