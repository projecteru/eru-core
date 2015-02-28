# coding: utf-8


def test_version(client):
    from eru import __VERSION__
    rv = client.get('/api/sys/')
    assert rv.status_code == 200
    assert 'sys control' in rv.data
    
    rv = client.get('/api/deploy/')
    assert rv.status_code == 200
    assert 'deploy control' in rv.data

    rv = client.get('/')
    assert rv.status_code == 200
    assert 'Eru %s' % __VERSION__ == rv.data

