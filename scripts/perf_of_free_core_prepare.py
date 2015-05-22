#!/usr/bin/env python
# encoding: utf-8

from eru.app import create_app_with_celery
from eru.models import db, Group, Pod, Host, App
from tests.utils import random_ipv4, random_string, random_uuid, random_sha1

host_number = int(raw_input("how many hosts: "))

app, _ = create_app_with_celery
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost:3306/erutest'

with app.app_context():
    db.create_all()
    
    a = App.get_or_create('app', 'http://git.hunantv.com/group/app.git', '')
    v = a.add_version(random_sha1())
    g = Group.create('group', 'group')
    p = Pod.create('pod', 'pod', 10, -1)
    p.assigned_to_group(g)
    hosts = [Host.create(p, random_ipv4(), random_string(), random_uuid(), 24, 4096) for i in range(host_number)]
    
    for host in hosts:
        host.assigned_to_group(g)
