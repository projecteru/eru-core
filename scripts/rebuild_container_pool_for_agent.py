# coding: utf-8
from functools import wraps

from eru.app import create_app_with_celery
from eru.async.task import add_container_for_agent
from eru.models import Host
from eru.connection import rds


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


@with_app_context
def rebuild_container_pool():
    hosts = Host.query.all()
    for host in hosts:
        key = 'eru:agent:%s:containers:meta' % host.name
        rds.delete(key)
        for c in host.containers.all():
            add_container_for_agent(c)


if __name__ == '__main__':
    rebuild_container_pool()
