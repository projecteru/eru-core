# coding: utf-8

class FakeEtcd(object):

    def __init__(self, *a, **kw):
        self._data = {}

    def get(self, key, **kw):
        return self._data.get(key, None)
    read = get

    def set(self, key, value, ttl=None, dir=False, append=False, **kw):
        self._data[key] = value
    write = set

