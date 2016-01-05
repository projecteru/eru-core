# coding: utf-8

import time
from eru.models import Pod, Host
from eru.helpers.scheduler import get_max_container_count
from eru.helpers.scheduler import average_schedule
from eru.helpers.scheduler import centralized_schedule
from tests.utils import random_ipv4, random_uuid, random_string

def _create_data(core_share, max_share_core, host_count):
    pod = Pod.create('pod', 'pod', core_share, max_share_core)
    for _ in range(host_count):
        Host.create(pod, random_ipv4(), random_string(), random_uuid(), 16, 4096)
    return pod

def test_scheduler(test_db):
    # 10000个16核, 不限制共享数
    pod = _create_data(10, -1, 10000)


    start = time.time()
    assert get_max_container_count(pod, ncore=1, nshare=0) == 160000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=2, nshare=0) == 80000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=3, nshare=0) == 50000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=4, nshare=0) == 40000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=5, nshare=0) == 30000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=1, nshare=5) == 100000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=2, nshare=5) == 60000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=3, nshare=5) == 40000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=1, nshare=1) == 140000
    print time.time() - start

    start = time.time()
    assert get_max_container_count(pod, ncore=2, nshare=1) == 70000
    print time.time() - start

    start = time.time()
    assert len(average_schedule(pod, ncontainer=100, ncore=2)) == 100
    print time.time() - start

    start = time.time()
    assert len(average_schedule(pod, ncontainer=130, ncore=0, nshare=5)) == 130
    print time.time() - start

    start = time.time()
    r = average_schedule(pod, ncontainer=10, ncore=1)
    print time.time() - start
    assert len(r) == 10
    assert sum(i[1] for i in r.keys()) == 10
    for (host, count), cores in r.iteritems():
        assert len(cores['full']) == 1
        assert len(cores['part']) == 0

    start = time.time()
    r = average_schedule(pod, ncontainer=10000, ncore=2)
    print time.time() - start
    assert len(r) == 10000
    assert sum(i[1] for i in r.keys()) == 10000
    for (host, count), cores in r.iteritems():
        assert count == 1
        assert len(cores['full']) == 2
        assert len(cores['part']) == 0

    start = time.time()
    r = average_schedule(pod, ncontainer=10000, ncore=1, nshare=5)
    print time.time() - start
    assert len(r) == 10000
    assert sum(i[1] for i in r.keys()) == 10000
    for (host, count), cores in r.iteritems():
        assert count == 1 
        assert len(cores['full']) == 1
        assert len(cores['part']) == 1

    start = time.time()
    r = average_schedule(pod, ncontainer=10000, ncore=2, nshare=3)
    print time.time() - start
    assert len(r) == 10000
    assert sum(i[1] for i in r.keys()) == 10000
    for (host, count), cores in r.iteritems():
        assert count == 1
        assert len(cores['full']) == 2
        assert len(cores['part']) == 1

    start = time.time()
    assert len(centralized_schedule(pod, ncontainer=100, ncore=2)) == 13
    print time.time() - start
    start = time.time()
    assert len(centralized_schedule(pod, ncontainer=130, ncore=0, nshare=5)) == 5
    print time.time() - start

    start = time.time()
    r = centralized_schedule(pod, ncontainer=10000, ncore=1)
    print time.time() - start
    assert len(r) == 625
    assert sum(i[1] for i in r.keys()) == 10000
    for (host, count), cores in r.iteritems():
        assert count == 16
        assert len(cores['full']) == 16
        assert len(cores['part']) == 0

    start = time.time()
    r = centralized_schedule(pod, ncontainer=100, ncore=2)
    print time.time() - start
    assert len(r) == 13
    assert sum(i[1] for i in r.keys()) == 100
    for (host, count), cores in r.iteritems():
        assert count in (4, 8)
        if count == 4:
            assert len(cores['full']) == 8
            assert len(cores['part']) == 0
        if count == 8:
            assert len(cores['full']) == 16
            assert len(cores['part']) == 0

    start = time.time()
    r = centralized_schedule(pod, ncontainer=30, ncore=1, nshare=5)
    print time.time() - start
    assert len(r) == 3
    assert sum(i[1] for i in r.keys()) == 30
    for (host, count), cores in r.iteritems():
        assert count == 10
        assert len(cores['full']) == 10
        assert len(cores['part']) == 10
        assert len(set(cores['part'])) == 5

    start = time.time()
    r = centralized_schedule(pod, ncontainer=20, ncore=2, nshare=3)
    print time.time() - start
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
