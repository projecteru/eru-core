# coding: utf-8

import logging
import retrying
from werkzeug.security import gen_salt

from eru.agent import get_agent

logger = logging.getLogger(__name__)


@retrying.retry(retry_on_result=lambda r: not r, stop_max_attempt_number=5)
def _bind_container_ip_http(task_id, container, ips, nid=None):
    agent = get_agent(container.host)
    ip_list = [(nid or ip.vlan_seq_id, ip.vlan_address) for ip in ips]
    resp = agent.add_container_vlan(container.container_id, str(task_id), ip_list)

    if resp.status_code != 200:
        return False

    for result in resp.json():
        if result['succ'] == 0:
            break
        ip.set_vethname(result['veth'])
    else:
        return True

    return False


def bind_container_ip(container, ips, nid=None):
    """
    nid就是network的id.
    为了防止agent那边生成重复的nid, 需要覆盖掉默认的nid的值.
    """
    if not ips:
        return

    task_id = gen_salt(10)
    try:
        _bind_container_ip_http(task_id, container, ips, nid=nid)
    except retrying.RetryError:
        logger.info('still failed after 5 times retry, %s, %s' % (container.container_id, ips))
        pass


def rebind_container_ip(container):
    ips = container.ips.all()
    bind_container_ip(container, ips)
