# coding: utf-8

from eru.storage.base import BaseConfigStorage


class RedisStorage(BaseConfigStorage):

    def __init__(self, redis):
        self._client = redis

    def set(self, key, value, ttl=None):
        return self._client.set(key, value, ex=ttl)

    def get(self, key):
        return self._client.get(key)

    def write(self, key, value, ttl=None, **kwargs):
        return self.set(key, value, ttl)

