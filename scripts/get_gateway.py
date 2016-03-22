# coding: utf-8
import sys
from functools import wraps

from netaddr import IPAddress

from eru.app import create_app_with_celery
from eru.models import Network, VLanGateway, Host
from eru.connection import rds


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


def take_gateway(netspace, ip, host):
    net = Network.get_by_netspace(netspace)
    if not net:
        print 'net %s not found' % netspace
        return
    ipnum = IPAddress(ip).value
    rds.srem(net.gatekey, ipnum)
    VLanGateway.create(ipnum, net.id, host.id)
    print '%s on %s --> %s done' % (ip, host.ip, netspace)


@with_app_context
def take_one(host_ip, netspace, vlan_ip):
    host = Host.get_by_addr(host_ip + ':2376')
    if not host:
        print 'host %s not found' % host_ip
    take_gateway(netspace, vlan_ip, host)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'python get_gateway.py host_ip, netspace vlan_ip'
        sys.exit(0)
    take_one(sys.argv[1], sys.argv[2], sys.argv[3])
