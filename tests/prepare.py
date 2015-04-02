# coding: utf-8

import requests
from eru.models import App, Group, Pod, Host, Container
from tests.utils import random_sha1, random_string, random_uuid, random_ipv4


def create_test_suite():
    appyaml = {
        'appname': 'app',
        'entrypoints': {
            'web': {
                'cmd': 'python app.py',
                'ports': ['5000/tcp'],
            },
            'daemon': {
                'cmd': 'python daemon.py',
            },
            'service': {
                'cmd': 'python service.py'
            },
        },
        'build': 'pip install -r ./requirements.txt',
    }
    app = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', 'token')
    version = app.add_version(random_sha1())
    appconfig = version.appconfig
    appconfig.update(**appyaml)
    appconfig.save()

    group = Group.create('group', 'group')
    pod = Pod.create('pod', 'pod')
    pod.assigned_to_group(group)

    hosts = [Host.create(pod, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(4)]

    for host in hosts:
        host.assigned_to_group(group)

    containers = []
    for (host, count), cores in group.get_free_cores(pod, 4, 4).iteritems():
        cores_per_container = len(cores) / count
        for i in range(count):
            cid = random_sha1()
            used_cores = cores[i*cores_per_container:(i+1)*cores_per_container]
            c = Container.create(cid, host, version, random_string(), 'entrypoint', used_cores, 'env')
            containers.append(c)
        host.occupy_cores(cores)
    return app, version, group, pod, hosts, containers


def create_local_test_data(private=False):
    appyaml = {
        'appname': 'blueberry',
        'entrypoints': {
            'web': {
                'cmd': 'python app.py',
                'ports': ['5000/tcp'],
            },
            'daemon': {
                'cmd': 'python daemon.py',
            },
            'service': {
                'cmd': 'python service.py'
            },
        },
        'build': 'pip install -r ./requirements.txt',
    }
    app = App.get_or_create('blueberry', 'http://git.hunantv.com/tonic/blueberry.git', 'token')
    version = app.add_version('abe23812aeb50a17a2509c02a28423462161d306')
    appconfig = version.appconfig
    appconfig.update(**appyaml)
    appconfig.save()

    group = Group.create('group', 'group')
    pod = Pod.create('pod', 'pod')
    pod.assigned_to_group(group)

    r = requests.get('http://192.168.59.103:2375/info').json()
    host = Host.create(pod, '192.168.59.103:2375', r['Name'], r['ID'], r['NCPU'], r['MemTotal'])

    if private:
        host.assigned_to_group(group)

    return app, version, group, pod, host

