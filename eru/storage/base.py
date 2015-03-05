# coding: utf-8


class BaseConfigStorage(object):

    def set(self, key, value, ttl=None):
        raise NotImplementedError()

    def get(self, key):
        """should return string or None"""
        raise NotImplementedError()

    def list(self, key):
        raise NotImplementedError()

