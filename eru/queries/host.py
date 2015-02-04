#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc

import settings
from eru.models import db, Pod, Host, Cpu, Group, Port

logger = logging.getLogger(__name__)

def create_host(pod_name, addr, name, uid, ncpu, mem):
    pod = Pod.query.filter_by(name=pod_name).first()
    if not pod:
        return False
    host = Host(addr, name, uid, ncpu, mem)
    try:
        pod.hosts.append(host)
        [host.cpus.append(Cpu()) for i in xrange(ncpu)]
        for i in xrange(settings.PORT_START, settings.PORT_START+settings.PORT_NUM):
            host.ports.append(Port(i))
        db.session.add(host)
        db.session.add(pod)
        db.session.commit()
        return True
    except sqlalchemy.exe, e:
        db.session.rollback()
        logging.exception(e)
        return False

def assign_group(name, addr):
    host = Host.query.filter_by(addr=addr).first()
    group = Group.query.filter_by(name=name).first()
    if not host or not group:
        return False
    group.hosts.append(host)
    db.session.add(group)
    db.session.commit()
    return True

