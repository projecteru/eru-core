#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc
from eru.models import db, Group, Pod, Cpu, Host

logger = logging.getLogger(__name__)

def create_group(name, description=""):
    group = Group(name, description)
    try:
        db.session.add(group)
        db.session.commit()
        return group
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        logger.exception(e)
        return None

def assign_pod(group_name, pod_name):
    group = Group.query.filter_by(name=group_name).first()
    pod = Pod.query.filter_by(name=pod_name).first()
    if not group or not pod:
        return False
    group.pods.append(pod)
    db.session.add(group)
    db.session.commit()
    return True

def get_group_max_containers(name, need):
    hosts = Host.query.filter(Host.group.has(name=name)).all()
    if not hosts:
        return 0
    m = 0
    for host in hosts:
        cpus= Cpu.query.filter(Cpu.host.has(id=host.id)).filter_by(used=0).count()
        m = m + cpus/need
    return m

