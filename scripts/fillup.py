# coding: utf-8

import requests

from eru.app import create_app_with_celery
from eru.models import db, Group, Pod, Host, App

def fillup_data():
    app, _ = create_app_with_celery()
    with app.app_context():
        db.drop_all()
        db.create_all()

        group = Group.create('test-group', 'test-group')
        pod = Pod.create('test-pod', 'test-pod')
        pod.assigned_to_group(group)

        r = requests.get('http://192.168.59.103:2375/info').json()
        host = Host.create(pod, '192.168.59.103:2375', r['Name'], r['ID'], r['NCPU'], r['MemTotal'])
        host.assigned_to_group(group)

        app = App.get_or_create('nbetest', 'http://git.hunantv.com/platform/nbetest.git', 'token')
        app.add_version('96cbf8c68ed214f105d9f79fa4f22f0e80e75cf3')
        app.assigned_to_group(group)
        version = app.get_version('96cbf8')


if __name__ == '__main__':
    fillup_data()

