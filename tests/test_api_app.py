# coding: utf-8

import json
import yaml

from tests.utils import random_string, random_sha1
from tests.mock import FakeEtcd

def test_create_app(client, test_db, monkeypatch):
    monkeypatch.setattr('eru.models.appconfig.config_backend', FakeEtcd())

    appyaml = '''
appname: "test_app"
entrypoints:
    web:
        cmd: "python app.py --port 5000"
        ports:
            - 5000/tcp
    daemon:
        cmd: "python daemon.py --interval 5"
    service:
        cmd: "go run service.go"
build: "pip install -r ./req.txt"
'''
    data = {
        'version': random_sha1(),
        'git': 'http://git.huanntv.com/test_app.git',
        'token': random_string(random_size=10),
        'appyaml': yaml.load(appyaml),
    }
    rv = client.post('/api/app/register/', data=json.dumps(data), content_type='application/json')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert r[u'r'] == 0
    assert r[u'msg'] == u'ok'
    
    rv = client.get('/api/app/test_app/')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert r[u'name'] == u'test_app'
    assert r[u'git'] == data['git']
    assert r[u'token'] == data['token']
    assert r[u'group_id'] is None

    rv = client.get('/api/app/random_app_name/')
    r = json.loads(rv.data)
    assert rv.status_code == 404
    assert r[u'error'] == 'App random_app_name not found'

    rv = client.get('/api/app/{0}/{1}/'.format('test_app', data['version']))
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert r[u'name'] == u'test_app'
    assert r[u'sha'] == data['version']
    assert r[u'appconfig']['appname'] == u'test_app'
    assert len(r[u'appconfig']['entrypoints']) == 3
    assert r[u'appconfig']['entrypoints']['web']['cmd'] == u'python app.py --port 5000'
    assert r[u'appconfig']['entrypoints']['web']['ports'] == ['5000/tcp']
    assert r[u'appconfig']['entrypoints']['daemon']['cmd'] == u'python daemon.py --interval 5'
    assert r[u'appconfig']['entrypoints']['service']['cmd'] == u'go run service.go'
    assert r[u'appconfig']['build'] == u'pip install -r ./req.txt'

    # 短 version 试试
    rv = client.get('/api/app/{0}/{1}/'.format('test_app', data['version'][:7]))
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert r[u'name'] == u'test_app'
    assert r[u'sha'] == data['version']

def test_app_env(client, test_db, monkeypatch):
    monkeypatch.setattr('eru.models.appconfig.config_backend', FakeEtcd())

    appyaml = '''
appname: "test_app"
entrypoints:
    web:
        cmd: "python app.py --port 5000"
        ports:
            - 5000/tcp
    daemon:
        cmd: "python daemon.py --interval 5"
    service:
        cmd: "go run service.go"
build: "pip install -r ./req.txt"
'''
    data = {
        'version': random_sha1(),
        'git': 'http://git.huanntv.com/test_app.git',
        'token': random_string(random_size=10),
        'appyaml': yaml.load(appyaml),
    }
    client.post('/api/app/register/', data=json.dumps(data), content_type='application/json')
    rv = client.get('/api/app/test_app/')
    assert rv.status_code == 200

    url = '/api/app/{0}/env/'.format('test_app')
    envdata = {
        'env': 'prod',
        'TEST_APP_REDIS': 'test_app_redis',
        'TEST_APP_MYSQL': 'test_app_mysqldsn',
    }
    rv = client.put(url, data=json.dumps(envdata), content_type='application/json')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert r[u'r'] == 0
    assert r[u'msg'] == u'ok'

    rv = client.get(url+'?env=prod')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert r[u'r'] == 0
    assert r[u'msg'] == u'ok'
    assert r[u'data']['TEST_APP_REDIS'] == 'test_app_redis'
    assert r[u'data']['TEST_APP_MYSQL'] == 'test_app_mysqldsn'

    # 没有 env 应该挂
    envdata.pop('env')
    rv = client.put(url, data=json.dumps(envdata), content_type='application/json')
    r = json.loads(rv.data)
    assert rv.status_code == 400
    assert r[u'error'].startswith('env must be')

    rv = client.get(url)
    r = json.loads(rv.data)
    assert rv.status_code == 400
    assert r[u'error'].startswith('env must be in request.args')

    # 错误的 env 返回空的
    rv = client.get(url+'?env=xxx')
    r = json.loads(rv.data)
    assert rv.status_code == 200
    assert not r['data']
