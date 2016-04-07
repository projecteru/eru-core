# coding: utf-8

import operator
from collections import Counter

from eru.utils.decorator import redis_lock


def get_max_container_count(pod, ncore, nshare=0):
    if nshare and not pod.max_share_core:
        return 0
    return sum(host.get_max_container_count(ncore, nshare) for host in pod.get_private_hosts())


@redis_lock('scheduler:{pod.id}')
def average_schedule(pod, ncontainer, ncore, nshare=0, spec_host=None):
    if nshare and not pod.max_share_core:
        return {}

    if spec_host:
        count, rs = spec_host.get_container_cores(ncontainer, ncore, nshare)
        return {(spec_host, count): rs} if count else {}

    if ncontainer > get_max_container_count(pod, ncore, nshare):
        return {}

    result = {}
    hosts = pod.get_private_hosts()

    host_counter = Counter()
    used_counter = Counter()

    for host in hosts:
        count = host.get_max_container_count(ncore, nshare)
        if count:
            host_counter[host] = count

    still_need = ncontainer
    while still_need > 0:
        for host, count in host_counter.iteritems():
            if count:
                used_counter[host] += 1
                host_counter[host] -= 1
                still_need -= 1
                if still_need == 0:
                    break
    for host, count in used_counter.iteritems():
        result[(host, count)] = host.get_container_cores(count, ncore, nshare)[1]
    return result


@redis_lock('scheduler:{pod.id}')
def centralized_schedule(pod, ncontainer, ncore, nshare=0, spec_host=None):
    if nshare and not pod.max_share_core:
        return {}

    if spec_host:
        count, rs = spec_host.get_container_cores(ncontainer, ncore, nshare)
        return {(spec_host, count): rs} if count else {}

    if ncontainer > get_max_container_count(pod, ncore, nshare):
        return {}

    result = {}
    hosts = pod.get_private_hosts()
    sorted(hosts, key=operator.attrgetter('count'))
    still_need = ncontainer
    for host in hosts:
        count, rs = host.get_container_cores(still_need, ncore, nshare)
        if count:
            result[(host, count)] = rs
            still_need -= count
            if still_need <= 0:
                break

    return result
