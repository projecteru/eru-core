# coding: utf-8

from eru.models import App, Group, Pod, Host, Container

from tests.utils import random_sha1, random_string, random_uuid, random_ipv4


def create_test_suite():
    a = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', '')
    v = a.add_version(random_sha1())
    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod')
    p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(4)]
    for host in hosts:
        host.assigned_to_group(g)
    containers = []
    for (host, count), cores in g.get_free_cores(p, 4, 4).iteritems():
        cores_per_container = len(cores) / count
        for i in range(count):
            cid = random_sha1()
            used_cores = cores[i*cores_per_container:(i+1)*cores_per_container]
            c = Container.create(cid, host, v, random_string(), 'entrypoint', used_cores)
            containers.append(c)
        host.occupy_cores(cores)
    return a, v, g, p, hosts, containers

