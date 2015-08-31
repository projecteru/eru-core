# coding: utf-8

import json


def test_version(client):
    from eru import __VERSION__
    rv = client.get('/api/sys/')
    assert rv.status_code == 200
    assert 'sys control' in rv.data
    
    rv = client.get('/api/deploy/')
    assert rv.status_code == 200
    assert 'deploy control' in rv.data

    rv = client.get('/')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert __VERSION__ == r['version']
