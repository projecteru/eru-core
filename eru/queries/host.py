#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc

import settings
from eru.models import db, Pod, Host, Cpu, Group, Port
from eru.common.exc import NoHost, PortNotEnough

logger = logging.getLogger(__name__)

def create_host(pod_name, addr, name, uid, ncpu, mem):
    pod = Pod.query.filter_by(name=pod_name).first()
    if not pod:
        return None
    host = Host(addr, name, uid, ncpu, mem)
    try:
        pod.hosts.append(host)
        [host.cpus.append(Cpu()) for i in xrange(ncpu)]
        for i in xrange(settings.PORT_START, settings.PORT_START+host.ncpu*settings.PORT_RANGE):
            host.ports.append(Port(i))
        db.session.add(host)
        db.session.add(pod)
        db.session.commit()
        return host
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        logging.exception(e)
        return None

def assign_group(name, addr):
    host = Host.query.filter_by(addr=addr).first()
    group = Group.query.filter_by(name=name).first()
    if not host or not group:
        return False
    group.hosts.append(host)
    db.session.add(group)
    db.session.commit()
    return True

def get_host_cpus(group_name, pod_name, ncpu, ncontainer):
    hosts = Host.query \
            .filter(Host.group.has(name=group_name)) \
            .filter(Host.pod.has(name=pod_name)) \
            .all() \

    if not hosts:
        raise NoHost()

    result = {}
    for host in hosts:
        cpus = Cpu.query.filter(Cpu.host.has(id=host.id)).filter_by(used=0).all()
        can = len(cpus)/ncpu
        if can <= 0:
            continue
        if ncontainer <= can:
            return {(host, ncontainer): cpus[:ncontainer*ncpu]}
        result[(host, can)] = cpus
        ncontainer = ncontainer - can
    return result

def get_host_ports(expose, host, num):
    if not expose:
        return []
    ports = Port.query.filter(Port.host.has(id=host.id)).filter_by(used=0).limit(num).all()
    if len(ports) < num:
        raise PortNotEnough()
    return ports

def use_cpus(cpus):
    for cpu in cpus:
        cpu.use()
        db.session.add(cpu)
    db.session.commit()

def use_ports(ports):
    for port in ports:
        port.use()
        db.session.add(port)
    db.session.commit()

def release_cpus(cpus):
    for cpu in cpus:
        cpu.used = 0
        db.session.add(cpu)
    db.session.commit()

def release_ports(ports):
    for port in ports:
        port.used = 0
        db.session.add(port)
    db.session.commit()

