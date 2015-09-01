# coding: utf-8

import operator
from decimal import Decimal as D
from more_itertools import chunked

from eru.models import Group, Pod, Host, App, Container, Network, VLanGateway
from eru.helpers.scheduler import get_max_container_count, centralized_schedule

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
    assert get_max_container_count(g3, p3, 1, 2) == 0
    assert centralized_schedule(g3, p3, 1, 1, 2) == {}

def test_pod(test_db):
    p1 = Pod.create('p1', 'p1', core_share=10)
    assert p1 is not None
    assert p1.get_core_allocation(1) == (1, 0)
    assert p1.get_core_allocation(1.5) == (1, 5)
    assert p1.get_core_allocation(2) == (2, 0)
    assert p1.get_core_allocation(2.8) == (2, 8)
    assert p1.get_core_allocation(0.8) == (0, 8)
    assert p1.get_core_allocation(0.1) == (0, 1)

    p2 = Pod.create('p2', 'p2', core_share=100)
    assert p2 is not None
    assert p2.get_core_allocation(1) == (1, 0)
    assert p2.get_core_allocation(1.5) == (1, 50)
    assert p2.get_core_allocation(2) == (2, 0)
    assert p2.get_core_allocation(2.8) == (2, 80)
    assert p2.get_core_allocation(0.81) == (0, 81)
    assert p2.get_core_allocation(0.14) == (0, 14)

def test_host(test_db):
    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod', 10, -1)
    assert p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(6)]
    for host in hosts:
        assert host is not None
        assert len(host.cores) == 4
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 4
        assert len(part_cores) == 0

    assert len(g.private_hosts.all()) == 0
    assert get_max_container_count(g, p, 1, 0) == 0
    assert centralized_schedule(g, p, 1, 1, 0) == {}

    for host in hosts[:3]:
        host.assigned_to_group(g)
    host_ids1 = {h.id for h in hosts[:3]}
    host_ids2 = {h.id for h in hosts[3:]}

    assert len(g.private_hosts.all()) == 3
    assert get_max_container_count(g, p, 1, 0) == 12
    host_cores = centralized_schedule(g, p, 12, 1, 0)
    assert len(host_cores) == 3
    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 4
        assert len(cores['full']) == 4

    assert get_max_container_count(g, p, 3, 0) == 3
    host_cores = centralized_schedule(g, p, 3, 3, 0)
    assert len(host_cores) == 3
    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 1
        assert len(cores['full']) == 3

    assert get_max_container_count(g, p, 2, 0) == 6
    host_cores = centralized_schedule(g, p, 4, 2, 0)
    assert len(host_cores) == 2
    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 2
        assert len(cores['full']) == 4

    assert get_max_container_count(g, p, 1, 1) == 9
    host_cores = centralized_schedule(g, p, 3, 1, 1)
    assert len(host_cores) == 1
    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 3
        assert len(cores['full']) == 3
        assert len(cores['part']) == 3

    assert get_max_container_count(g, p, 2, 3) == 3
    host_cores = centralized_schedule(g, p, 3, 2, 3)
    assert len(host_cores) == 3
    for (host, count), cores in host_cores.iteritems():
        assert host.id in host_ids1
        assert host.id not in host_ids2
        assert count == 1
        assert len(cores['full']) == 2
        assert len(cores['part']) == 1

def test_container(test_db):
    a = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', '')
    assert a is not None
    assert a.id == a.user_id

    v = a.add_version(random_sha1())
    assert v is not None
    assert v.app.id == a.id
    assert v.name == a.name
    assert len(v.containers.all()) == 0
    assert len(v.tasks.all()) == 0

    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod', 10, -1)
    assert p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(prefix='host'),
        random_uuid(), 4, 4096) for i in range(6)]

    for host in hosts[:3]:
        host.assigned_to_group(g)
    host_ids1 = {h.id for h in hosts[:3]}
    host_ids2 = {h.id for h in hosts[3:]}

    host_cores = centralized_schedule(g, p, 3, 3, 0)

    #测试没有碎片核的情况
    #获取核
    containers = []
    for (host, count), cores in host_cores.iteritems():
        host.occupy_cores(cores, 0)
        cores_per_container = len(cores['full']) / count
        for i in range(count):
            cid = random_sha1()
            used_cores = {'full': cores['full'][i*cores_per_container:(i+1)*cores_per_container]}
            c = Container.create(cid, host, v, random_string(), 'entrypoint', used_cores, 'env', nshare=0)
            assert c is not None
            containers.append(c)

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
        assert len(c.full_cores) == 3
        assert len(c.part_cores) == 0
        all_core_labels = sorted(['0', '1', '2', '3', ])
        used_full_core_labels = [core.label for core in c.full_cores]
        used_part_core_labels = [core.label for core in c.part_cores]
        free_core_labels = [core.label for core in c.host.get_free_cores()[0]]
        assert all_core_labels == sorted(used_full_core_labels + used_part_core_labels + free_core_labels)

    #释放核
    for c in containers:
        c.delete()

    assert len(v.containers.all()) == 0
    assert get_max_container_count(g, p, 3, 0) == 3
    host_cores = centralized_schedule(g, p, 3, 3, 0)
    assert len(host_cores) == 3

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 4
        assert len(part_cores) == 0
        assert len(host.containers.all()) == 0
        assert host.count == 4

    #测试有碎片的情况
    #获取核
    host_cores = centralized_schedule(g, p, 3, 3, 4)
    containers = []
    for (host, count), cores in host_cores.iteritems():
        cores_per_container = len(cores['full']) / count
        host.occupy_cores(cores, 4)
        for i in range(count):
            cid = random_sha1()
            used_cores = {'full':  cores['full'][i*cores_per_container:(i+1)*cores_per_container],
                    'part': cores['part']}
            # not using a port
            c = Container.create(cid, host, v, random_string(), 'entrypoint', used_cores, 'env', nshare=4)
            assert c is not None
            containers.append(c)

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 0
        assert len(part_cores) == 1
        assert part_cores[0].remain == 6
        assert len(host.containers.all()) == 1
        assert host.count == D('0.6')

    assert len(containers) == 3
    assert len(v.containers.all()) == 3

    for c in containers:
        assert c.host_id in host_ids1
        assert c.host_id not in host_ids2
        assert c.app.id == a.id
        assert c.version.id == v.id
        assert c.is_alive
        assert len(c.full_cores) == 3
        assert len(c.part_cores) == 1
        all_core_labels = sorted(['0', '1', '2', '3', ])
        used_full_core_labels = [core.label for core in c.full_cores]
        used_part_core_labels = [core.label for core in c.part_cores]
        free_core_labels = [core.label for core in c.host.get_free_cores()[0]]
        assert all_core_labels == sorted(used_full_core_labels + used_part_core_labels + free_core_labels)

    #释放核
    for c in containers:
        c.delete()

    assert len(v.containers.all()) == 0
    assert get_max_container_count(g, p, 3, 0) == 3
    host_cores = centralized_schedule(g, p, 3, 3, 0)
    assert len(host_cores) == 3

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 4
        assert len(host.containers.all()) == 0
        assert host.count == 4

    #获取
    host_cores = centralized_schedule(g, p, 6, 1, 5)
    containers = []
    for (host, count), cores in host_cores.iteritems():
        cores_per_container = len(cores['full']) / count
        for i in range(count):
            cid = random_sha1()
            used_cores = {
                'full':  cores['full'][i*cores_per_container:(i+1)*cores_per_container],
                'part': cores['part'][i:i+1],
            }
            host.occupy_cores(used_cores, 5)
            # not using a port
            c = Container.create(cid, host, v, random_string(), 'entrypoint', used_cores, 'env', nshare=5)
            assert c is not None
            containers.append(c)

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 1
        assert len(part_cores) == 0
        assert len(host.containers.all()) == 2
        assert host.count == D('1')

    assert len(containers) == 6
    assert len(v.containers.all()) == 6

    for c in containers:
        assert c.host_id in host_ids1
        assert c.host_id not in host_ids2
        assert c.app.id == a.id
        assert c.version.id == v.id
        assert c.is_alive
        assert len(c.full_cores) == 1
        assert len(c.part_cores) == 1

    ##释放核
    for c in containers:
        c.delete()

    assert len(v.containers.all()) == 0
    assert get_max_container_count(g, p, 3, 0) == 3
    host_cores = centralized_schedule(g, p, 3, 3, 0)
    assert len(host_cores) == 3

    for host in g.private_hosts.all():
        full_cores, part_cores = host.get_free_cores()
        assert len(full_cores) == 4
        assert len(part_cores) == 0
        assert len(host.containers.all()) == 0
        assert host.count == 4

def test_occupy_and_release_cores(test_db):
    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod', 10, -1)
    host = Host.create(p, random_ipv4(), random_string(), random_uuid(), 200, 0)
    assert p.assigned_to_group(g)
    assert host.assigned_to_group(g)

    for core in host.cores:
        assert core.host_id == host.id
        assert core.remain == 10

    cores = {
        'full': host.cores[:100],
        'part': host.cores[100:],
    }

    host.occupy_cores(cores, 5)
    for core in host.cores[:100]:
        assert core.remain == 0
    for core in host.cores[100:]:
        assert core.remain == 5

    host.release_cores(cores, 5)
    for core in host.cores:
        assert core.remain == 10

    host.occupy_cores(cores, 8)
    for core in host.cores[:100]:
        assert core.remain == 0
    for core in host.cores[100:]:
        assert core.remain == 2

    host.release_cores(cores, 8)
    for core in host.cores:
        assert core.remain == 10

    cores = {
        'full': host.cores[:50],
        'part': host.cores[50:100],
    }

    host.occupy_cores(cores, 8)
    for core in host.cores[:50]:
        assert core.remain == 0
    for core in host.cores[50:100]:
        assert core.remain == 2

    host.release_cores(cores, 8)
    for core in host.cores:
        assert core.remain == 10

def test_container_release_cores(test_db):
    a = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', '')
    v = a.add_version(random_sha1())
    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod', 10, -1)
    host = Host.create(p, random_ipv4(), random_string(), random_uuid(), 200, 0)
    assert p.assigned_to_group(g)
    assert host.assigned_to_group(g)

    for core in host.cores:
        assert core.host_id == host.id
        assert core.remain == 10

    containers = []
    
    cores = sorted(host.cores, key=operator.attrgetter('label'))
    for fcores, pcores in zip(chunked(cores[:100], 10), chunked(cores[100:], 10)):
        used_cores = {'full': fcores, 'part': pcores}
        host.occupy_cores(used_cores, 5)
        c = Container.create(random_sha1(), host, v, random_string(), 'entrypoint', used_cores, 'env', nshare=5)
        containers.append(c)

    cores = sorted(host.cores, key=operator.attrgetter('label'))
    for fcores, pcores in zip(chunked(cores[:100], 10), chunked(cores[100:], 10)):
        for core in fcores:
            assert core.remain == 0
        for core in pcores:
            assert core.remain == 5

    for c in containers:
        c.delete()

    cores = sorted(host.cores, key=operator.attrgetter('label'))
    for fcores, pcores in zip(chunked(cores[:100], 10), chunked(cores[100:], 10)):
        for core in fcores:
            assert core.remain == 10
        for core in pcores:
            assert core.remain == 10

def test_network(test_db):
    n = Network.create('net', '10.1.0.0/16')
    assert n is not None
    assert len(n.ips.all()) == 0
    assert n.hostmask_string == '16'
    assert n.pool_size == 65436
    assert n.used_count == 0
    assert n.used_gate_count == 0
    assert n.gate_pool_size == 100

    ip = n.acquire_ip()
    assert ip is not None
    assert ip.network_id == n.id
    assert ip.vethname == ''
    assert not ip.container_id
    assert ip.hostmask == n.hostmask_string
    assert ip.vlan_seq_id == n.id
    assert ip.address.startswith('10.1')

    assert len(n.ips.all()) == 1
    assert n.pool_size == 65435
    assert n.used_count == 1

    ip.release()
    assert len(n.ips.all()) == 0
    assert n.pool_size == 65436
    assert n.used_count == 0

    p = Pod.create('pod', 'pod', 10, -1)
    host = Host.create(p, random_ipv4(), random_string(prefix='host'), random_uuid(), 4, 4096)

    gate = n.acquire_gateway_ip(host)
    assert gate is not None
    assert gate.network_id == n.id
    assert gate.vlan_address.startswith('10.1.0.')
    assert gate.vlan_seq_id == n.id
    assert gate.name == 'vlan.%02d.br' % n.id

    g = VLanGateway.get_by_host_and_network(host.id, n.id)
    assert g is not None
    assert g.id == gate.id
    assert len(host.list_vlans()) == 1

    assert n.used_gate_count == 1
    assert n.gate_pool_size == 99

    gate.release()
    assert n.used_gate_count == 0
    assert n.gate_pool_size == 100
    assert VLanGateway.get_by_host_and_network(host.id, n.id) is None
    assert len(host.list_vlans()) == 0
