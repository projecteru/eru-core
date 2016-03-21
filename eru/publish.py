# coding: utf-8

import json
import logging

from eru.redis_client import rds


_log = logging.getLogger(__name__)
_APP_BACKENDS_KEY = 'eru:app:%s:backends'
_APP_ENTRYPOINT_BACKENDS_KEY = 'eru:app:%s:entrypoint:%s:backends'
_APP_DISCOVERY_KEY = 'eru:discovery:published'
_AGENT_CONTAINER_KEY = 'eru:agent:%s:containers:meta'
_NO_REPORT_KEY = 'eru:agent:%s:container:flag'


def _app_key(container):
    return _APP_BACKENDS_KEY % container.appname


def _entrypoint_key(container):
    return _APP_ENTRYPOINT_BACKENDS_KEY % (container.appname, container.entrypoint)


def _agent_key(host):
    return _AGENT_CONTAINER_KEY % host.name


def add_container_backends(container):
    rds.hset(_app_key(container), container.entrypoint, _entrypoint_key(container))
    backends = container.get_backends()
    if backends:
        rds.sadd(_entrypoint_key(container), *backends)


def remove_container_backends(container):
    backends = container.get_backends()
    if backends:
        rds.srem(_entrypoint_key(container), *backends)


def add_container_for_agent(host, container):
    rds.hset(_agent_key(host), container.container_id, json.dumps(container.meta))


def remove_container_for_agent(host, container_ids):
    rds.hdel(_agent_key(host), *container_ids)


def publish_to_service_discovery(*appnames):
    for appname in appnames:
        rds.publish(_APP_DISCOVERY_KEY, appname)


def set_flag_for_agent(container_ids):
    flags = {_NO_REPORT_KEY % cid: 1 for cid in container_ids}
    rds.mset(**flags)


def remove_flag_for_agent(container_ids):
    flags = [_NO_REPORT_KEY % cid for cid in container_ids]
    rds.delete(*flags)
