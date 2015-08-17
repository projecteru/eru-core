# coding: utf-8

import requests

from eru.config import FALCON_API_HOST

SIX_HOURS = 3600 * 6

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

    try:
        requests.post(FALCON_API_HOST, data=data)
    except:
        pass

def falcon_cpu_graph(version):
    indicators = ['cpu_system_rate', 'cpu_usage_rate', 'cpu_user_rate']
    containers = version.list_containers(limit=None)

    entrypoints = set([c.entrypoint for c in containers])
    appname = version.name

    index = version.appconfig.get('falcon-index', 'basic')
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

    index = version.appconfig.get('falcon-index', 'basic')
    inbytes_counters = ','.join(['metric=%s.inbytes.rate __version__=%s' % (v, version.short_sha) for v in vethnames])
    outbytes_counters = ','.join(['metric=%s.outbytes.rate __version__=%s' % (v, version.short_sha) for v in vethnames])
    hosts = ','.join(['%s-%s' % (appname, e) for e in entrypoints])

    _add_falcon_graph(index, appname, inbytes_counters, hosts, title='inbytes')
    _add_falcon_graph(index, appname, outbytes_counters, hosts, title='outbytes')

def falcon_all_graphs(version):
    for f in [falcon_cpu_graph, falcon_mem_graph, falcon_network_graph]:
        f(version)
