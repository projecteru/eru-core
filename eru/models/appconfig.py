# coding: utf-8

import yaml
import ipaddress

from eru.clients import config_backend

__all__ = ['AppConfig', 'ResourceConfig', 'verify_appconfig', ]

"""
Example of app.yaml:

    appname: "app"
    entrypoints:
        web:
            cmd: "python app.py --port 5000"
            ports:
                - "5000/tcp"
                - "5001/udp"
            network_mode: "bridge"
            mem_limit: 5000
            restart: "on-failure"
        daemon:
            cmd: "python daemon.py --interval 5"
            network_mode: "host"
            network_route: "10.100.1.254"
        service:
            cmd: "python service.py"
    build: "pip install -r ./req.txt"
    volumes:
        - "/container/data1"
        - "/container/data2"
    binds:
        /host/data1:
            bind: "/container/data1"
            ro: false
        /host/data2:
            bind: "/container/data2"
            ro: true
    meta:
        meta_key1: meta_value1
        meta_key2: meta_value2
    falcon-index: "MPP"
    falcon-alarm:
        - "cpu_usage_rate"
        - "mem_usage"
"""

REQUIRED_KEYS = ['appname', 'entrypoints', 'build']
OPTIONAL_KEYS = ['volumes', 'binds']

FALCON_ALARM_KEY = ['cpu_system_rate', 'cpu_usage_rate', 'cpu_user_rate',
    'mem_max_usage', 'mem_usage', 'mem_rss', 'inbytes', 'outbytes',
]

def verify_appconfig(appconfig):
    for key in REQUIRED_KEYS:
        if key not in appconfig:
            raise KeyError('need %s set' % key)
    # check entrypoints
    entrypoints = appconfig['entrypoints']
    for entry, content in entrypoints.iteritems():
        if '_' in entry:
            raise ValueError('sorry but we do not support `_` in entrypoint 눈_눈')
        if not isinstance(content, dict):
            raise ValueError('entrypoint %s must be dictionary' % entry)
        if 'cmd' not in content:
            raise KeyError('need cmd set in entrypoint %s' % entry)

        ports = content.get('ports', [])
        if not isinstance(ports, list):
            raise ValueError('ports must be a list')

        for port in ports:
            if '/' not in port:
                raise ValueError('port must be formatted as port/protocol like 5000/tcp')
            po, proto = port.split('/', 1)
            if not po.isdigit():
                raise ValueError('port must be formatted as port/protocol like 5000/tcp')

        route = content.get('network_route', '')
        if route:
            try:
                ipaddress.ip_address(unicode(route))
            except ValueError:
                raise ValueError('network_route must be IPv4 address')

    # check build
    build = appconfig['build']
    if not isinstance(build, (basestring, list)):
        raise ValueError('build must be string or list')

    volumes = appconfig.get('volumes', [])
    if not isinstance(volumes, list):
        raise ValueError('volumes must be list')

    binds = appconfig.get('binds', {})
    if not isinstance(binds, dict):
        raise ValueError('volumes must be dictionary')

    if len(volumes) != len(binds):
        raise ValueError('volumes and binds must be 1 to 1 mapping')

    meta = appconfig.get('meta', {})
    if not isinstance(meta, dict):
        raise ValueError('meta must be dictionary')

    falcon_alarm_key = appconfig.get('falcon-alarm', [])
    if falcon_alarm_key and not all([key in FALCON_ALARM_KEY for key in falcon_alarm_key]):
        raise ValueError('invalid falcon alarm key')

    return True

class BaseConfig(object):

    list_names = []
    dict_names = []

    def __init__(self, path, **kw):
        self.path = path
        self._data = {}
        if kw:
            self._data.update(kw)

    @classmethod
    def _list_by_path(cls, path):
        info = config_backend.list(path) or []
        return info

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
        path = '/ERU/{0}/{1}/app.yaml'.format(name, version)
        return cls._get_by_path(path)

class ResourceConfig(BaseConfig):

    @classmethod
    def get_by_name_and_env(cls, name, env='prod'):
        path = '/ERU/{0}/resource/{1}'.format(name, env)
        return cls._get_by_path(path)

    @classmethod
    def list_env(cls, name):
        path = '/ERU/%s/resource' % name
        return cls._list_by_path(path)

    def to_env_dict(self):
        return {key.upper(): str(value) for key, value in self._data.iteritems()}
