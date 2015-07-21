# coding: utf-8

from functools import wraps

from eru.app import create_app_with_celery
from eru.models import Host, Container
from eru.async.task import add_container_for_agent


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


def migrate_container_set(host):
    containers = Container.get_multi_by_host(host)
    for c in containers:
        add_container_for_agent(c)


@with_app_context
def migrate_all_hosts():
    hosts = Host.query.all()
    for host in hosts:
        migrate_container_set(host)


if __name__ == '__main__':
    migrate_all_hosts()
