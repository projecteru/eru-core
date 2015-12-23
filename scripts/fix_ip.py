# coding: utf-8

import more_itertools
from functools import wraps

from eru.clients import rds
from eru.app import create_app_with_celery
from eru.models import Network


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


def fix_ip(n):
    network = n.network
    base = int(network.network_address)
    for ipnums in more_itertools.chunked(xrange(base+n.gateway_count, base+network.num_addressed), 500):
        rds.sadd(n.storekey, *ipnums)

    rds.sadd(n.gatekey, *range(base, base+n.gateway_count))

    for ip in n.ips.all():
        rds.srem(n.storekey, ip.ipnum)

    for gateway in n.gates.all():
        rds.srem(n.gatekey, gateway.ipnum)


@with_app_context
def fix_all_ips():
    networks = Network.query.all()
    for n in networks:
        fix_ip(n)


if __name__ == '__main__':
    fix_all_ips()
