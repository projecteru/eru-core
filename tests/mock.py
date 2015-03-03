# coding: utf-8

import contextlib

from tests.utils import random_sha1


class FakeEtcd(object):

    def __init__(self, *a, **kw):
        self._data = {}

    def get(self, key, **kw):
        return self._data.get(key, None)
    read = get

    def set(self, key, value, ttl=None, dir=False, append=False, **kw):
        self._data[key] = value
    write = set


class FakeCeleryTask(object):
    """直接执行celery"""
    def __init__(self, fn):
        self.fn = fn

    def apply_async(self, *a, **kw):
        print 'mocked, run directly'
        return self.fn(*a, **kw)

    __call__ = apply_async


class FakeCeleryCurrentApp(object):

    def task(self):
        def deco(f):
            return FakeCeleryTask(f)
        return deco


class FakeDockerClient(object):

    def __init__(self, *a, **kw):
        pass

    def build(self, *a, **kw):
        yield 'build successfully'

    def push(self, *a, **kw):
        yield 'push successfully'

    def create_container(self, *a, **kw):
        return {'Id': random_sha1()}

    def start(self, *a, **kw):
        pass


def fake_build_image(host, version, base):
    yield 'build successfully'


@contextlib.contextmanager
def fake_build_image_environment(version, base, rev):
    yield '%s %s %s' % (version.sha1, base, rev)

