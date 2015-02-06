#!/usr/bin/python
#coding:utf-8

import logging
from celery import current_app

from eru.common import code
from eru.queries import task

logger = logging.getLogger(__name__)

@current_app.task()
def create_container(t, cpus, ports):
    #TODO get docker deploy status
    try:
        # if suceess
        import time
        time.sleep(60)
    except Exception, e:
        logger.exception(e)
        task.release_cpus_ports(cpus, ports)
        task.done(t, code.TASK_FAILED)
    else:
        task.done(t, code.TASK_SUCCESS)
    # container.create()

