# coding:utf-8

from eru.clients import rds
from eru.consts import (
    ERU_TASK_PUBKEY,
    ERU_TASK_LOGKEY,
    ERU_TASK_RESULTKEY,
    ERU_AGENT_WATCHERKEY,
    TASK_RESULT_SUCCESS,
    TASK_RESULT_FAILED,
    PUB_END_MESSAGE,
)

class TaskNotifier(object):

    def __init__(self, task):
        self.task = task
        self.result_key = ERU_TASK_RESULTKEY % task.id
        self.log_key = ERU_TASK_LOGKEY % task.id
        self.publish_key = ERU_TASK_PUBKEY % task.id

    def pub_success(self):
        rds.publish(self.result_key, TASK_RESULT_SUCCESS)

    def pub_fail(self):
        rds.publish(self.result_key, TASK_RESULT_FAILED)

    def pub_build_finish(self):
        rds.publish(self.publish_key, PUB_END_MESSAGE)

    def store_and_broadcast(self, iterable):
        """iter完这个generator并且返回最后一个"""
        line = ''
        for line in iterable:
            rds.rpush(self.log_key, line)
            rds.publish(self.publish_key, line)
        return line

    def get_store_logs(self):
        return rds.lrange(self.log_key, 0, -1)

    def notify_agent(self, cid):
        watcher_key = ERU_AGENT_WATCHERKEY % self.task.host.name
        message = '+|%s' % cid
        rds.publish(watcher_key, message)

