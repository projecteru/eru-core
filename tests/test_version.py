# coding: utf-8

from pytest import fixture


def test_version(client):
    rv = client.get('/sys/')
    assert rv.status_code == 200
    assert 'sys control' in rv.data
    
    rv = client.get('/deploy/')
    assert rv.status_code == 200
    assert 'deploy control' in rv.data

