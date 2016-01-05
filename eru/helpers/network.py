# coding: utf-8

import logging
import retrying

from eru.ipam import ipam

_log = logging.getLogger(__name__)


@retrying.retry(retry_on_result=lambda r: not r, stop_max_attempt_number=5)
def _bind_container_ip(cidrs, container, spec_ips=None):
    return ipam.allocate_ips(cidrs, container.container_id, spec_ips=spec_ips)


def bind_container_ip(container, cidrs, spec_ips=None):
    try:
        _bind_container_ip(cidrs, container, spec_ips=spec_ips)
    except retrying.RetryError:
        _log.info('still failed after 5 times retry, %s, %s' % (container.container_id, cidrs))
        pass


@retrying.retry(retry_on_result=lambda r: not r, stop_max_attempt_number=5)
def _rebind_container_ip(container):
    return ipam.reallocate_ips(container.container_id)


def rebind_container_ip(container):
    try:
        _rebind_container_ip(container)
    except retrying.RetryError:
        _log.info('still failed after 5 times retry, %s' % container.container_id)
        pass
