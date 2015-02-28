# coding: utf-8

class FakeEtcdNode(object):

    def __init__(self, value):
        self.value = value
        self.dir = False

class FakeEtcd(object):

    def __init__(self, *a, **kw):
        self._data = {}

    def get(self, key, **kw):
        return FakeEtcdNode(self._data[key])
    read = get

    def set(self, key, value, ttl=None, dir=False, append=False, **kw):
        self._data[key] = value
    write = set

