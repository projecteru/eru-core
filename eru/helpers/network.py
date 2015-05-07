# coding: utf-8

# TODO: 其实应该需要一个序列发生器
from res.ext.common import random_string

from eru.common.clients import rds

# TODO retry till success?
#@retrying.retry
def rebind_container_ip(container):
    task_id = random_string(10)
    pub_agent_vlan_key = 'eru:agent:%s:vlan' % container.host.name
    feedback_key = 'eru:agent:%s:feedback' % task_id

    ips = container.ips.all()
    if not ips:
        return

    values = [task_id, container.container_id, container.ident_id]
    values += ['{0}:{1}'.format(ip.vlan_seq_id, ip.vlan_address) for ip in ips]
    rds.publish(pub_agent_vlan_key, '|'.join(values))

    for _ in ips:
        rv = rds.blpop(feedback_key, 15)
        if rv is None:
            break
        succ = rv[1].split('|')[0]
        if succ == '0':
            break

    rds.delete(feedback_key)
