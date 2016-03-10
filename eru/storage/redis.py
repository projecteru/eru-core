# coding: utf-8
from eru.storage.base import BaseConfigStorage


class RedisStorage(BaseConfigStorage):

    def __init__(self, redis):
        self._client = redis

    def set(self, key, value, ttl=None):
        return self._client.set(key, value, ex=ttl)

    def get(self, key):
        name, key = key.rsplit('/', 1)
        return self._client.hget(name, key)

    def write(self, key, value, ttl=None, **kwargs):
        name, key = key.rsplit('/', 1)
        return self._client.hset(name, key, value)

    def list(self, key):
        return self._client.hkeys(key)

    def delete(self, key):
        name, key = key.rsplit('/', 1)
        return self._client.hdel(name, key)
