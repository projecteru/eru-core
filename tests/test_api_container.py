# coding: utf-8

import json
from tests.prepare import create_test_suite

def test_container_kill(client, test_db):
    # kill 永远对外成功.
    rv = client.put('/api/container/12345/kill')
    assert rv.status_code == 200
    d = json.loads(rv.data)
    assert d['msg'] == u'ok'
    assert d['r'] == 0

def test_container_poll(client, test_db):
    rv = client.get('/api/container/12345/poll')
    assert rv.status_code == 404
    d = json.loads(rv.data)
    assert d['error'] == 'Container 12345 not found'

def test_container_status(client, test_db):
    app, version, pod, hosts, containers = create_test_suite()
    for c in containers:
        rv = client.get('/api/container/%s/poll' % c.container_id)
        assert rv.status_code == 200
        d = json.loads(rv.data)
        assert d['r'] == 0
        assert d['container'] == c.container_id
        assert d['status'] == 1
        assert c.is_alive == 1

    for c in containers:
        assert c.is_alive == 1
        rv = client.put('/api/container/%s/kill' % c.container_id)
        assert rv.status_code == 200
        d = json.loads(rv.data)
        assert d['r'] == 0
        assert d['msg'] == 'ok'
        assert c.is_alive == 0

    for c in containers:
        rv = client.get('/api/container/%s/poll' % c.container_id)
        assert rv.status_code == 200
        d = json.loads(rv.data)
        assert d['r'] == 0
        assert d['container'] == c.container_id
        assert d['status'] == 0

