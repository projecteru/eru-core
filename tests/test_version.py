# coding: utf-8

import json

def test_version(client):
    from eru import __VERSION__
    rv = client.get('/')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert __VERSION__ == r['version']
