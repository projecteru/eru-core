# coding: utf-8

import requests

from eru.app import create_app_with_celery
from eru.models import db, Group, Pod, Host, App, Task

def fillup_data():
    app, _ = create_app_with_celery()
    with app.app_context():
        db.drop_all()
        db.create_all()

        group = Group.create('test-group', 'test-group')
        pod = Pod.create('test-pod', 'test-pod')
        pod.assigned_to_group(group)

        r = requests.get('http://192.168.59.103:2375/info').json()
        host = Host.create(pod, '192.168.59.103:2375', r['Name'], r['ID'], r['NCPU'], r['MemTotal'])
        host.assigned_to_group(group)

        app = App.get_or_create('nbetest', 'http://git.hunantv.com/platform/nbetest.git', 'token')
        app.add_version('96cbf8c68ed214f105d9f79fa4f22f0e80e75cf3')
        app.assigned_to_group(group)
        version = app.get_version('96cbf8')

        host_cores = group.get_free_cores(pod, 2, 2)
        cores = []
        for (host, cn), coress in host_cores.iteritems():
            print host, cn, coress
            cores = coress
        print cores
        ports = host.get_free_ports(2)
        print ports
        props = {
            'entrypoint': 'web',
            'ncontainer': 2,
            'env': 'PROD',
            'cores': [c.id for c in cores],
            'ports': [p.id for p in ports],
        }
        task = Task.create(1, version, host, props)
        print task.props
        host.occupy_cores(cores)
        host.occupy_ports(ports)
        print group.get_free_cores(pod, 1, 1)


if __name__ == '__main__':
    fillup_data()

