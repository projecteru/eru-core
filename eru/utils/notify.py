#!/usr/bin/python
#coding:utf-8

import logging

from eru.common import code
from eru.common.clients import rds
from eru.common.settings import ERU_AGENT_CONTAINERSKEY, ERU_AGENT_WATCHERKEY
from eru.common.settings import ERU_TASK_PUBKEY, ERU_TASK_LOGKEY, ERU_TASK_RESULTKEY

logger = logging.getLogger(__name__)

class TaskNotifier(object):

    def __init__(self, task):
        self.task = task
        self.result_key = ERU_TASK_RESULTKEY % task.id
        self.log_key = ERU_TASK_LOGKEY % task.id
        self.publish_key = ERU_TASK_PUBKEY % task.id

    def on_success(self):
        rds.publish(self.result_key, code.TASK_RESULT_SUCCESS)

    def on_failed(self):
        rds.publish(self.result_key, code.TASK_RESULT_FAILED)

    def on_build_finish(self):
        rds.publish(self.publish_key, code.PUB_END_MESSAGE)

    def store_and_broadcast(self, lines):
        for line in lines:
            rds.rpush(self.log_key, line)
            rds.publish(self.publish_key, line)

    def get_store_logs(self):
        return rds.lrange(self.log_key, 0, -1)

    def notify_agent(self, cid, type=1):
        flag = '+' if type else '-'
        containers_key = ERU_AGENT_CONTAINERSKEY % self.task.host.addr
        watcher_key = ERU_AGENT_WATCHERKEY % self.task.host.addr
        message = '%s|%s' % (flag, cid)
        rds.rpush(containers_key, cid)
        rds.publish(watcher_key, message)

