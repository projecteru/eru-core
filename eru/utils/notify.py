#!/usr/bin/python
#coding:utf-8

import logging

from eru.common import code
from eru.common.clients import rds
from eru.common.settings import (ERU_AGENT_WATCHERKEY,
        ERU_TASK_PUBKEY, ERU_TASK_LOGKEY, ERU_TASK_RESULTKEY)

logger = logging.getLogger(__name__)

class TaskNotifier(object):

    def __init__(self, task):
        self.task = task
        self.result_key = ERU_TASK_RESULTKEY % task.id
        self.log_key = ERU_TASK_LOGKEY % task.id
        self.publish_key = ERU_TASK_PUBKEY % task.id

    def pub_success(self):
        rds.publish(self.result_key, code.TASK_RESULT_SUCCESS)

    def pub_fail(self):
        rds.publish(self.result_key, code.TASK_RESULT_FAILED)

    def pub_build_finish(self):
        rds.publish(self.publish_key, code.PUB_END_MESSAGE)

    def store_and_broadcast(self, iterable):
        for line in iterable:
            rds.rpush(self.log_key, line)
            rds.publish(self.publish_key, line)

    def get_store_logs(self):
        return rds.lrange(self.log_key, 0, -1)

    def notify_agent(self, cid):
        watcher_key = ERU_AGENT_WATCHERKEY % self.task.host.name
        message = '+|%s' % cid
        rds.publish(watcher_key, message)

