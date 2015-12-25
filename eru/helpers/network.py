# coding: utf-8

import logging
import retrying

from eru.ipam import ipam

logger = logging.getLogger(__name__)


@retrying.retry(retry_on_result=lambda r: not r, stop_max_attempt_number=5)
def _bind_container_ip_http(cidrs, container):
    return ipam.allocate_ips(cidrs, container.container_id)


def bind_container_ip(container, cidrs):
    try:
        _bind_container_ip_http(cidrs, container)
    except retrying.RetryError:
        logger.info('still failed after 5 times retry, %s, %s' % (container.container_id, cidrs))
        pass


def rebind_container_ip(container):
    ips = container.ips.all()
    cidrs = [ip.network.netspace for ip in ips]
    bind_container_ip(container, cidrs)
