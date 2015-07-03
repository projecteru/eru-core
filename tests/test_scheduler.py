# coding: utf-8

from eru.models import Group, Pod, Host
from eru.helpers.scheduler import get_max_container_count
from eru.helpers.scheduler import average_schedule
from eru.helpers.scheduler import centralized_schedule
from tests.utils import random_ipv4, random_uuid, random_string

def _create_data(core_share, max_share_core, host_count):
    group = Group.create('group', 'group')
    pod = Pod.create('pod', 'pod', core_share, max_share_core)
    for _ in range(host_count):
        host = Host.create(pod, random_ipv4(), random_string(), random_uuid(), 16, 4096)
        host.assigned_to_group(group)
    return group, pod

def test_get_max_container_count(test_db):
    # 4个16核, 不限制共享数
    group, pod = _create_data(10, -1, 4)
    assert get_max_container_count(group, pod, ncore=1, nshare=0) == 64
    assert get_max_container_count(group, pod, ncore=2, nshare=0) == 32
    assert get_max_container_count(group, pod, ncore=3, nshare=0) == 20
    assert get_max_container_count(group, pod, ncore=4, nshare=0) == 16
    assert get_max_container_count(group, pod, ncore=5, nshare=0) == 12
    assert get_max_container_count(group, pod, ncore=1, nshare=5) == 40
    assert get_max_container_count(group, pod, ncore=2, nshare=5) == 24
    assert get_max_container_count(group, pod, ncore=3, nshare=5) == 16
    assert get_max_container_count(group, pod, ncore=1, nshare=1) == 56
    assert get_max_container_count(group, pod, ncore=2, nshare=1) == 28

def test_get_max_container_count_single_host(test_db):
    group = Group.create('group', 'group')
    pod = Pod.create('pod', 'pod', 10, -1)
    host = Host.create(pod, random_ipv4(), random_string(), random_uuid(), 64, 4096)
    host.assigned_to_group(group)

    assert get_max_container_count(group, pod, ncore=1, nshare=0) == 64
    assert get_max_container_count(group, pod, ncore=2, nshare=0) == 32
    assert get_max_container_count(group, pod, ncore=3, nshare=0) == 21
    assert get_max_container_count(group, pod, ncore=4, nshare=0) == 16
    assert get_max_container_count(group, pod, ncore=5, nshare=0) == 12
    assert get_max_container_count(group, pod, ncore=1, nshare=5) == 42
    assert get_max_container_count(group, pod, ncore=2, nshare=5) == 25

def test_host_get_container_cores(test_db):
    group, pod = _create_data(10, -1, 1)
    host = pod.hosts.all()[0]

    total, rs = host.get_container_cores(1, 1, 0)
    assert total == 1
    assert len(rs['full']) == 1
    assert len(rs['part']) == 0

    total, rs = host.get_container_cores(100, 1, 0)
    assert total == 16
    assert len(rs['full']) == 16
    assert len(rs['part']) == 0

    total, rs = host.get_container_cores(10, 2, 0)
    assert total == 8
    assert len(rs['full']) == 16
    assert len(rs['part']) == 0

    total, rs = host.get_container_cores(2, 3, 0)
    assert total == 2
    assert len(rs['full']) == 6
    assert len(rs['part']) == 0

    total, rs = host.get_container_cores(2, 3, 0)
    assert total == 2
    assert len(rs['full']) == 6
    assert len(rs['part']) == 0

    total, rs = host.get_container_cores(2, 3, 5)
    assert total == 2
    assert len(rs['full']) == 6
    assert len(rs['part']) == 2
    assert len(set(rs['part'])) == 1

    total, rs = host.get_container_cores(5, 1, 7)
    assert total == 5
    assert len(rs['full']) == 5
    assert len(rs['part']) == 5
    assert len(set(rs['part'])) == 5

    total, rs = host.get_container_cores(6, 1, 3)
    assert total == 6
    assert len(rs['full']) == 6
    assert len(rs['part']) == 6
    assert len(set(rs['part'])) == 2

def test_average_schedule(test_db):
    # 4个16核, 不限制共享数
    group, pod = _create_data(10, -1, 4)

    assert len(average_schedule(group, pod, ncontainer=100, ncore=2)) == 0
    assert len(average_schedule(group, pod, ncontainer=130, ncore=0, nshare=5)) == 0

    r = average_schedule(group, pod, ncontainer=10, ncore=1)
    assert len(r) == 4
    assert sum(i[1] for i in r.keys()) == 10
    for (host, count), cores in r.iteritems():
        assert count in (2, 3)
        if count == 2:
            assert len(cores['full']) == 2
            assert len(cores['part']) == 0
        if count == 3:
            assert len(cores['full']) == 3
            assert len(cores['part']) == 0

    r = average_schedule(group, pod, ncontainer=9, ncore=2)
    assert len(r) == 4
    assert sum(i[1] for i in r.keys()) == 9
    for (host, count), cores in r.iteritems():
        assert count in (2, 3)
        if count == 2:
            assert len(cores['full']) == 4
            assert len(cores['part']) == 0
        if count == 3:
            assert len(cores['full']) == 6
            assert len(cores['part']) == 0

    r = average_schedule(group, pod, ncontainer=40, ncore=1, nshare=5)
    assert len(r) == 4
    assert sum(i[1] for i in r.keys()) == 40
    for (host, count), cores in r.iteritems():
        assert count == 10 
        assert len(cores['full']) == 10
        assert len(cores['part']) == 10
        assert len(set(cores['part'])) == 5

    r = average_schedule(group, pod, ncontainer=22, ncore=2, nshare=3)
    assert len(r) == 4
    assert sum(i[1] for i in r.keys()) == 22
    for (host, count), cores in r.iteritems():
        assert count in (5, 6)
        if count == 5:
            assert len(cores['full']) == 10
            assert len(cores['part']) == 5
            assert len(set(cores['part'])) == 2
        if count == 6:
            assert len(cores['full']) == 12
            assert len(cores['part']) == 6
            assert len(set(cores['part'])) == 2

def test_centralized_schedule(test_db):
    # 4个16核, 不限制共享数
    group, pod = _create_data(10, -1, 4)

    assert len(centralized_schedule(group, pod, ncontainer=100, ncore=2)) == 0
    assert len(centralized_schedule(group, pod, ncontainer=130, ncore=0, nshare=5)) == 0

    r = centralized_schedule(group, pod, ncontainer=10, ncore=1)
    assert len(r) == 1
    assert sum(i[1] for i in r.keys()) == 10
    for (host, count), cores in r.iteritems():
        assert count == 10
        assert len(cores['full']) == 10
        assert len(cores['part']) == 0

    r = centralized_schedule(group, pod, ncontainer=9, ncore=2)
    assert len(r) == 2
    assert sum(i[1] for i in r.keys()) == 9
    for (host, count), cores in r.iteritems():
        assert count in (1, 8)
        if count == 1:
            assert len(cores['full']) == 2
            assert len(cores['part']) == 0
        if count == 8:
            assert len(cores['full']) == 16
            assert len(cores['part']) == 0

    r = centralized_schedule(group, pod, ncontainer=30, ncore=1, nshare=5)
    assert len(r) == 3
    assert sum(i[1] for i in r.keys()) == 30
    for (host, count), cores in r.iteritems():
        assert count == 10
        assert len(cores['full']) == 10
        assert len(cores['part']) == 10
        assert len(set(cores['part'])) == 5

    r = centralized_schedule(group, pod, ncontainer=20, ncore=2, nshare=3)
    assert len(r) == 4
    assert sum(i[1] for i in r.keys()) == 20
    for (host, count), cores in r.iteritems():
        assert count in (2, 6)
        if count == 2:
            assert len(cores['full']) == 4
            assert len(cores['part']) == 2
            assert len(set(cores['part'])) == 1
        if count == 6:
            assert len(cores['full']) == 12
            assert len(cores['part']) == 6
            assert len(set(cores['part'])) == 2
