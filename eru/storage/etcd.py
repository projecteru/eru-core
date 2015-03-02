# coding: utf-8

from eru.storage.base import BaseConfigStorage


class EtcdStorage(BaseConfigStorage):

    def __init__(self, etcd):
        self._client = etcd

    def set(self, key, value, ttl=None):
        return self._client.set(key, value, ttl)

    def write(self, key, value, ttl=None, **kwargs):
        return self._client.write(key, value, ttl, **kwargs)

    def get(self, key):
        try:
            r = self._client.get(key)
            return r.value if (r and not r.dir) else None
        except KeyError:
            return None

