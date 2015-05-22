#!/usr/bin/env python
# encoding: utf-8

import time
from eru.app import create_app_with_celery
from eru.models import db, Group, Pod, App

num_of_containers = int(raw_input("how many containers: "))
num_of_cores = int(raw_input("how many cores: "))
num_of_part_cores = int(raw_input("how many part_cores: "))

app, _ = create_app_with_celery()
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost:3306/erutest'
ctx = app.app_context()
ctx.push()

a = App.query.first()
g = Group.query.first()
p = Pod.query.first()
v = a.versions.first()

time_1 = time.time()
host_cores = g.get_free_cores(p, num_of_containers, num_of_cores, num_of_part_cores)

time_2 = time.time()
for (host, count), cores in host_cores.iteritems():
    host.occupy_cores(cores, num_of_part_cores)
time_3 = time.time()

print len(host_cores)
print "get_free_cores: {0}".format(time_2 - time_1)
print "occupy_cores: {0}".format(time_3 - time_2)

for (host, count), cores in host_cores.iteritems():
    host.release_cores(cores, num_of_part_cores)

db.session.remove()
ctx.pop()
