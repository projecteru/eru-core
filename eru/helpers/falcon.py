# coding: utf-8

import json
import requests

from eru.config import FALCON_API_HOST

SIX_HOURS = 3600 * 6
DEFAULT_INDEX = 'eru'
_100MB = 100 * 1024 * 1024
_10GB = 10 * 1024 * 1024 * 1024
_20GB = 20 * 1024 * 1024 * 1024

def _add_falcon_graph(index, screen, counters, hosts,
        title, graph_type='k', timespan=SIX_HOURS):
    if not FALCON_API_HOST:
        return
    if not (counters and hosts):
        return

    data = {}
    data['index'] = index
    data['screen'] = screen
    data['counters'] = counters
    data['hosts'] = hosts
    data['title'] = title
    data['graph_type'] = graph_type
    data['timespan'] = timespan

    url = '%s/api/add_screen_graph' % FALCON_API_HOST
    try:
        requests.post(url, data=data)
    except:
        pass

def falcon_cpu_graph(version):
    indicators = ['cpu_system_rate', 'cpu_usage_rate', 'cpu_user_rate']
    containers = version.list_containers(limit=None)

    entrypoints = set([c.entrypoint for c in containers])
    appname = version.name

    index = version.appconfig.get('falcon-index', DEFAULT_INDEX)
    counters = ','.join(['metric=%s __version__=%s' % (m, version.short_sha) for m in indicators])
    hosts = ','.join(['%s-%s' % (appname, e) for e in entrypoints])

    _add_falcon_graph(index, appname, counters, hosts, title='cpu')

def falcon_mem_graph(version):
    indicators = ['mem_max_usage', 'mem_usage', 'mem_rss']
    containers = version.list_containers(limit=None)

    entrypoints = set([c.entrypoint for c in containers])
    appname = version.name

    index = version.appconfig.get('falcon-index', 'basic')
    counters = ','.join(['metric=%s __version__=%s' % (m, version.short_sha) for m in indicators])
    hosts = ','.join(['%s-%s' % (appname, e) for e in entrypoints])

    _add_falcon_graph(index, appname, counters, hosts, title='mem')

def falcon_network_graph(version):
    containers = version.list_containers(limit=None)

    entrypoints = set([c.entrypoint for c in containers])
    vethnames = set([ip.vethname for c in containers for ip in c.ips])
    appname = version.name

    index = version.appconfig.get('falcon-index', DEFAULT_INDEX)
    inbytes_counters = ','.join(['metric=%s.inbytes.rate __version__=%s' % (v, version.short_sha) for v in vethnames])
    outbytes_counters = ','.join(['metric=%s.outbytes.rate __version__=%s' % (v, version.short_sha) for v in vethnames])
    hosts = ','.join(['%s-%s' % (appname, e) for e in entrypoints])

    _add_falcon_graph(index, appname, inbytes_counters, hosts, title='inbytes')
    _add_falcon_graph(index, appname, outbytes_counters, hosts, title='outbytes')

def falcon_all_graphs(version):
    for f in [falcon_cpu_graph, falcon_mem_graph, falcon_network_graph]:
        f(version)

def _add_falcon_alarm(metric, version, value):
    if not (metric and version):
        return

    data = {}
    data['op'] = '>'
    data['callback'] = '0'
    data['max_step'] = '3'
    data['func'] = 'all(#3)'
    data['priority'] = '0'
    data['right_value'] = value
    data['before_callback_mail'] = '0'
    data['after_callback_sms'] = '0'
    data['after_callback_mail'] = '0'
    data['uic'] = 'nbe'
    data['expression'] = 'each(metric=%s __version__=%s)' % (metric, version)

    url = '%s/api/add_alarm_expression' % FALCON_API_HOST
    try:
        r = requests.post(url, data=data, timeout=7)
        return json.loads(r.content)['data']['expression_id']
    except:
        return 0

def falcon_all_alarms(version):
    __version__ = version.short_sha
    containers = version.list_containers(limit=None)
    vethnames = set([ip.vethname for c in containers for ip in c.ips])

    exp_ids = set()
    for vethname in vethnames:
        exp_ids.add(_add_falcon_alarm('%s.inbytes.rate' % vethname, version.short_sha, _100MB))
        exp_ids.add(_add_falcon_alarm('%s.outbytes.rate' % vethname, version.short_sha, _100MB))

    exp_ids.add(_add_falcon_alarm('cpu_system_rate', __version__, '90'))
    exp_ids.add(_add_falcon_alarm('cpu_usage_rate', __version__, '90'))
    exp_ids.add(_add_falcon_alarm('cpu_user_rate', __version__, '90'))
    exp_ids.add(_add_falcon_alarm('mem_max_usage', __version__, _20GB))
    exp_ids.add(_add_falcon_alarm('mem_usage', __version__, _10GB))

    version.falcon_expression_ids = [i for i in exp_ids if i]

def falcon_remove_alarms(version):
    for exp_id in version.falcon_expression_ids:
        try:
            requests.post('%s/api/delete_expression' % FALCON_API_HOST, data={'id': exp_id})
        except:
            pass
    del version.falcon_expression_ids
