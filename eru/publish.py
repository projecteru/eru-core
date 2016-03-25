# coding: utf-8

import json
import logging
import functools
from etcd import EtcdException

from eru.connection import rds, etcd
from eru.models.app import App


_log = logging.getLogger(__name__)

_APP_BACKENDS_KEY = 'eru:app:%s:backends'
_APP_ENTRYPOINT_BACKENDS_KEY = 'eru:app:%s:entrypoint:%s:backends'
_APP_DISCOVERY_KEY = 'eru:discovery:published'
_AGENT_CONTAINER_KEY = 'eru:agent:%s:containers:meta'
_NO_REPORT_KEY = 'eru:agent:%s:container:flag'


def handle_exception(f):
    @functools.wraps(f)
    def _(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (EtcdException, ValueError, KeyError):
            return None
    return _


def squash_dict(d):
    r = {}
    for sha, version in d.iteritems():
        for entry_name, entrypoint in version.iteritems():
            if entrypoint['addresses'] or entrypoint['backends']:
                r.setdefault(sha, {}).setdefault(entry_name, {})['addresses'] = entrypoint['addresses']
                r.setdefault(sha, {}).setdefault(entry_name, {})['backends'] = entrypoint['backends']
    return r


class EtcdPublisher(object):
    """
    完整路径是 /eru/service-nodes/:appname
    为了方便其他人读, 直接把所有信息存放在 :appname 下
    """
    APP_PATH = '/eru/service-nodes/%s'

    @classmethod
    @handle_exception
    def read(cls, path):
        return etcd.read(path)

    @classmethod
    @handle_exception
    def write(cls, path, value):
        return etcd.write(path, value)

    def get_app(self, appname):
        path = self.APP_PATH % appname
        r = self.read(path)
        return r and json.loads(r.value) or None

    def add_container(self, container):
        app = self.get_app(container.appname) or {}

        addresses = container.get_ips()
        backends = container.get_backends()

        current_addresses = app.get(container.short_sha, {}).get(container.entrypoint, {}).get('addresses', [])
        current_backends = app.get(container.short_sha, {}).get(container.entrypoint, {}).get('backends', [])

        new_addresses = list(set(current_addresses) | set(addresses))
        new_backends = list(set(current_backends) | set(backends))

        entrypoint = app.setdefault(container.short_sha, {}).setdefault(container.entrypoint, {})
        entrypoint['addresses'] = new_addresses
        entrypoint['backends'] = new_backends

        path = self.APP_PATH % container.appname
        self.write(path, json.dumps(squash_dict(app)))

    def remove_container(self, container):
        app = self.get_app(container.appname)
        if not app:
            return

        addresses = container.get_ips()
        backends = container.get_backends()

        current_addresses = app.get(container.short_sha, {}).get(container.entrypoint, {}).get('addresses', [])
        current_backends = app.get(container.short_sha, {}).get(container.entrypoint, {}).get('backends', [])

        new_addresses = list(set(current_addresses).difference(set(addresses)))
        new_backends = list(set(current_backends).difference(set(backends)))

        entrypoint = app.setdefault(container.short_sha, {}).setdefault(container.entrypoint, {})
        entrypoint['addresses'] = new_addresses
        entrypoint['backends'] = new_backends

        path = self.APP_PATH % container.appname
        self.write(path, json.dumps(squash_dict(app)))

    def publish_app(self, appname):
        app = App.get_by_name(appname)
        if not app:
            return

        data = {}
        for c in app.list_containers(limit=None):
            entrypoint = data.setdefault(c.short_sha, {}).setdefault(c.entrypoint, {})
            entrypoint['addresses'] = c.get_ips()
            entrypoint['backends'] = c.get_backends()

        path = self.APP_PATH % appname
        self.write(path, json.dumps(squash_dict(data)))


etcd_publisher = EtcdPublisher()


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

    #etcd_publisher.add_container(container)


def remove_container_backends(container):
    backends = container.get_backends()
    if backends:
        rds.srem(_entrypoint_key(container), *backends)

    #etcd_publisher.remove_container(container)


def add_container_for_agent(host, container):
    rds.hset(_agent_key(host), container.container_id, json.dumps(container.meta))


def remove_container_for_agent(host, container_ids):
    rds.hdel(_agent_key(host), *container_ids)


def publish_to_service_discovery(*appnames):
    for appname in appnames:
        rds.publish(_APP_DISCOVERY_KEY, appname)
        etcd_publisher.publish_app(appname)


def set_flag_for_agent(container_ids):
    flags = {_NO_REPORT_KEY % cid: 1 for cid in container_ids}
    rds.mset(**flags)


def remove_flag_for_agent(container_ids):
    flags = [_NO_REPORT_KEY % cid for cid in container_ids]
    rds.delete(*flags)
