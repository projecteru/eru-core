# coding: utf-8
from functools import wraps

from eru.app import create_app_with_celery
from eru.models import Host, Container
from eru.models.host import _create_cores_on_host
from eru.redis_client import rds


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


def fix_core(host):
    containers = Container.get_multi_by_host(host)

    # 没有的话, 直接销毁重建
    if not containers:
        _create_cores_on_host(host, host.ncore)
        return

    data = {str(i): host.core_share for i in xrange(host.ncore)}

    for c in containers:
        cores = c.cores
        nshare = int(cores.get('nshare', '0'))
        for e in cores.get('full', []):
            e.remain = host.core_share
            data.pop(e.label)
        for s in cores.get('part', []):
            s.remain = host.core_share - nshare
            data[s.label] -= nshare
        c.cores = cores
    rds.delete(host._cores_key)
    if data:
        rds.zadd(host._cores_key, **data)
    print 'done', host


@with_app_context
def fix_all_hosts_core():
    hosts = Host.query.all()
    for host in hosts:
        if not host.pod:
            continue
        fix_core(host)


if __name__ == '__main__':
    fix_all_hosts_core()
