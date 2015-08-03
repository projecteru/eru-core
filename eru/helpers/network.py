# coding: utf-8

import logging
import retrying
from res.ext.common import random_string

from eru.clients import rds
from eru.agent import get_agent
from eru.config import ERU_AGENT_API

logger = logging.getLogger(__name__)

@retrying.retry(retry_on_result=lambda r: not r, stop_max_attempt_number=5)
def _bind_container_ip_pubsub(task_id, container, ips, nid=None):
    pub_agent_vlan_key = 'eru:agent:%s:vlan' % container.host.name
    feedback_key = 'eru:agent:%s:feedback' % task_id

    values = [task_id, container.container_id]
    values += ['{0}:{1}'.format(nid or ip.vlan_seq_id, ip.vlan_address) for ip in ips]

    rds.publish(pub_agent_vlan_key, '|'.join(values))
    for _ in ips:
        rv = rds.blpop(feedback_key, 15)
        if rv is None:
            break
        succ = rv[1].split('|')[0]
        if succ == '0':
            break
    else:
        return True

    rds.delete(feedback_key)
    return False

@retrying.retry(retry_on_result=lambda r: not r, stop_max_attempt_number=5)
def _bind_container_ip_http(task_id, container, ips, nid=None):
    agent = get_agent(container.host)
    feedback_key = 'eru:agent:%s:feedback' % task_id

    ip_list = [(nid or ip.vlan_seq_id, ip.vlan_address) for ip in ips]
    agent.add_container_vlan(container.container_id, str(task_id), ip_list)

    for _ in ips:
        rv = rds.blpop(feedback_key, 15)
        if rv is None:
            break
        succ = rv[1].split('|')[0]
        if succ == '0':
            break
    else:
        return True

    rds.delete(feedback_key)
    return False

def bind_container_ip(container, ips, nid=None):
    """
    nid就是network的id.
    为了防止agent那边生成重复的nid, 需要覆盖掉默认的nid的值.
    """
    if not ips:
        return

    task_id = random_string(10)
    try:
        if ERU_AGENT_API == 'pubsub':
            _bind_container_ip_pubsub(task_id, container, ips, nid=nid)
        elif ERU_AGENT_API == 'http':
            _bind_container_ip_http(task_id, container, ips, nid=nid)
    except retrying.RetryError:
        logger.info('still failed after 5 times retry')
        pass

def rebind_container_ip(container):
    ips = container.ips.all()
    bind_container_ip(container, ips)
