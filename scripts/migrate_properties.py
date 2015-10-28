# coding: utf-8

import json
from functools import wraps

from eru.app import create_app_with_celery
from eru.models import Container, Task


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


@with_app_context
def migrate():
    containers = Container.query.all()
    for c in containers:
        c.props = json.loads(c.properties)

    tasks = Task.query.all()
    for t in tasks:
        t.props = json.loads(t.properties)


if __name__ == '__main__':
    migrate()
