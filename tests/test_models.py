# coding: utf-8

from eru.models import Group, Pod, Host, App, Container, Network
from tests.utils import random_ipv4, random_string, random_uuid, random_sha1

def test_group_pod(test_db):
    g1 = Group.create('group1', 'group1')
    g2 = Group.create('group1', 'group1')
    assert g1 is not None
    assert g1.name == 'group1'
    assert g2 is None

    p1 = Pod.create('pod1', 'pod1')
    p2 = Pod.create('pod1', 'pod1')
    assert p1 is not None
    assert p1.name == 'pod1'
    assert p2 is None

    g3 = Group.get_by_name('group1')
    assert g3.id == g1.id

    p3 = Pod.get_by_name('pod1')
    assert p3.id == p1.id

    assert p3.assigned_to_group(g3)
    assert p3.get_free_public_hosts(10) == []
    assert g3.get_max_containers(p3, 1, 2) == 0
    assert g3.get_free_cores(p3, 1, 1, 2) == {}

def test_host(test_db):
    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod')
    assert p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(6)]
    for host in hosts:
        assert host is not None
        assert len(host.cores.all()) == 4
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 4
        assert len(part_cores) == 0

    assert len(g.private_hosts.all()) == 0
    assert g.get_max_containers(p, 1, 0) == 0
    assert g.get_free_cores(p, 1, 1, 0) == {}

    for host in hosts[:3]:
        host.assigned_to_group(g)
    host_ids1 = {h.id for h in hosts[:3]}
    host_ids2 = {h.id for h in hosts[3:]}

    assert len(g.private_hosts.all()) == 3
    assert g.get_max_containers(p, 1, 0) == 12
    host_cores = g.get_free_cores(p, 12, 1, 0)
    assert len(host_cores) == 3

    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 4
        assert len(cores['full']) == 4

    assert g.get_max_containers(p, 3, 0) == 3
    host_cores = g.get_free_cores(p, 3, 3, 0)
    assert len(host_cores) == 3

    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 1
        assert len(cores['full']) == 3

    assert g.get_max_containers(p, 2, 0) == 6
    host_cores = g.get_free_cores(p, 4, 2, 0)
    assert len(host_cores) == 2

    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 2
        assert len(cores['full']) == 4

def test_container(test_db):
    a = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', '')
    assert a is not None

    v = a.add_version(random_sha1())
    assert v is not None
    assert v.app.id == a.id
    assert v.name == a.name
    assert len(v.containers.all()) == 0
    assert len(v.tasks.all()) == 0

    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod')
    assert p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(6)]

    for host in hosts[:3]:
        host.assigned_to_group(g)
    host_ids1 = {h.id for h in hosts[:3]}
    host_ids2 = {h.id for h in hosts[3:]}

    assert g.get_max_containers(p, 3, 0) == 3
    host_cores = g.get_free_cores(p, 3, 3, 0)
    assert len(host_cores) == 3

    containers = []
    for (host, count), cores in host_cores.iteritems():
        cores_per_container = len(cores['full']) / count
        for i in range(count):
            cid = random_sha1()
            used_cores = cores['full'][i*cores_per_container:(i+1)*cores_per_container]
            # not using a port
            c = Container.create(cid, host, v, random_string(), 'entrypoint', used_cores, 'env')
            assert c is not None
            containers.append(c)
        host.occupy_cores(cores, 0)

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 1
        assert len(part_cores) == 0
        assert len(host.containers.all()) == 1
        assert host.count == 1

    assert len(containers) == 3
    assert len(v.containers.all()) == 3

    for c in containers:
        assert c.host_id in host_ids1
        assert c.host_id not in host_ids2
        assert c.app.id == a.id
        assert c.version.id == v.id
        assert c.is_alive
        assert len(c.cores.all()) == 3
        all_core_labels = sorted(['0', '1', '2', '3', ])
        used_core_labels = [core.label for core in c.cores.all()]
        free_core_labels = [core.label for core in c.host.get_free_cores()[0]]
        assert all_core_labels == sorted(used_core_labels + free_core_labels)

    for c in containers:
        c.delete()

    assert len(v.containers.all()) == 0
    assert g.get_max_containers(p, 3, 0) == 3
    host_cores = g.get_free_cores(p, 3, 3, 0)
    assert len(host_cores) == 3

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 4
        assert len(part_cores) == 0
        assert len(host.containers.all()) == 0
        assert host.count == 0

def test_container_transform(test_db):
    a = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', '')
    assert a is not None

    v = a.add_version(random_sha1())
    v2 = a.add_version(random_sha1())
    assert v is not None
    assert v.app.id == a.id
    assert v.name == a.name
    assert len(v.containers.all()) == 0
    assert len(v.tasks.all()) == 0

    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod')
    assert p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(6)]

    for host in hosts[:3]:
        host.assigned_to_group(g)

    assert g.get_max_containers(p, 3, 0) == 3
    host_cores = g.get_free_cores(p, 3, 3, 0)
    assert len(host_cores) == 3

    containers = []
    for (host, count), cores in host_cores.iteritems():
        cores_per_container = len(cores) / count
        for i in range(count):
            cid = random_sha1()
            used_cores = cores['full'][i*cores_per_container:(i+1)*cores_per_container]
            c = Container.create(cid, host, v, random_string(), 'entrypoint', used_cores, 'env')
            assert c is not None
            containers.append(c)
        host.occupy_cores(cores, 0)

    for host in g.private_hosts.all():
        assert len(host.get_free_cores()[0]) == 1
        assert len(host.containers.all()) == 1
        assert host.count == 1

    assert len(containers) == 3
    assert len(v.containers.all()) == 3

    cids = [c.container_id for c in containers]
    for c in containers:
        host = c.host
        cid = c.container_id
        c.transform(v2, random_sha1(), random_string())
        assert c.container_id != cid

    new_cids = [c.container_id for c in containers]
    assert new_cids != cids

def test_network(test_db):
    n = Network.create('net', '10.1.0.0/16')
    assert n is not None
    assert len(n.ips.all()) == 0
    assert n.hostmask_string == '16'
    assert n.pool_size == 65535
    assert n.used_count == 0

    ip = n.acquire_ip()
    assert ip is not None
    assert ip.network_id == n.id
    assert ip.vethname == ''
    assert not ip.container_id
    assert ip.hostmask == n.hostmask_string
    assert ip.vlan_seq_id == n.id
    assert ip.address.startswith('10.1')

    assert len(n.ips.all()) == 1
    assert n.pool_size == 65534
    assert n.used_count == 1

    ip.release()
    assert len(n.ips.all()) == 0
    assert n.pool_size == 65535
    assert n.used_count == 0
