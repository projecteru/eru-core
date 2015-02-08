# coding: utf-8

import etcd
import yaml

__all__ = ['AppConfig', 'ResourceConfig', ]

# TODO: from config.py
_etcd_client = etcd.Client(host='10.1.201.110', port=4001)


class BaseConfig(object):

    list_names = []
    dict_names = []

    def __init__(self, path, **kw):
        self.path = ''
        self._data = {}
        if kw:
            self._data.update(kw)

    @classmethod
    def _get_by_path(cls, path):
        try:
            r = _etcd_client.get(path)
            config = r.value if (r and not r.dir) else '{}'
        except KeyError:
            config = '{}'
        if not config:
            config = '{}'
        config = yaml.load(config)
        return cls(path, **config)

    def __getitem__(self, name):
        if name in self.list_names:
            default = []
        elif name in self.dict_names:
            default = {}
        else:
            default = None
        return self._data.get(name, default)

    def __setitem__(self, name, value):
        self._data[name] = value

    __getattr__ = __getitem__
    __setattr__ = __setitem__

    def get(self, name, default=None):
        return self._data.get(name, default)

    def save(self):
        value = yaml.safe_dump(self._data, default_flow_style=False, indent=4)
        _etcd_client.write(self.path, value)


class AppConfig(BaseConfig):

    list_names = ['test', 'build', 'cmd', ]

    @classmethod
    def get_by_name_and_version(cls, name, version):
        path = '/NBE/{0}/{1}/app.yaml'.format(name, version)
        return cls._get_by_path(path)


class ResourceConfig(BaseConfig):

    @classmethod
    def get_by_name_and_env(cls, name, env='prod'):
        path = '/NBE/{0}/resource-{1}'.format(name, env)
        return cls._get_by_path(path)

