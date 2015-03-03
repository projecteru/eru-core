# coding: utf-8

import yaml

from eru.common.clients import config_backend

__all__ = ['AppConfig', 'ResourceConfig', ]

"""
Example of app.yaml:

    appname: "app"
    entrypoints:
        web:
            cmd: "python app.py --port 5000"
            port: 5000
        daemon:
            cmd: "python daemon.py --interval 5"
        service:
            cmd: "python service.py"
    build: "pip install -r ./req.txt"

"""


class BaseConfig(object):

    list_names = []
    dict_names = []

    def __init__(self, path, **kw):
        self.path = path
        self._data = {}
        if kw:
            self._data.update(kw)

    @classmethod
    def _get_by_path(cls, path):
        config = config_backend.get(path) or '{}'
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

    def update(self, **kw):
        self._data.update(kw)

    def get(self, name, default=None):
        return self._data.get(name, default)

    def save(self):
        value = yaml.safe_dump(self._data, default_flow_style=False, indent=4)
        config_backend.write(self.path, value)

    def to_dict(self):
        return self._data


class AppConfig(BaseConfig):

    dict_names = ['entrypoints', ]

    @classmethod
    def get_by_name_and_version(cls, name, version):
        path = '/NBE/{0}/{1}/app.yaml'.format(name, version)
        return cls._get_by_path(path)


class ResourceConfig(BaseConfig):

    @classmethod
    def get_by_name_and_env(cls, name, env='prod'):
        path = '/NBE/{0}/resource-{1}'.format(name, env)
        return cls._get_by_path(path)

    def to_env_dict(self):
        return {key.upper(): str(value) for key, value in self._data.iteritems()}

