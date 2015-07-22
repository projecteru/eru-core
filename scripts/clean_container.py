# coding: utf-8

import sys
from functools import wraps

from eru.app import create_app_with_celery
from eru.consts import TASK_REMOVE
from eru.models import Task, App
from eru.async.task import remove_containers


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


@with_app_context
def clean_app(app_name):
    app = App.get_by_name(app_name)
    if not app:
        print 'app %s not found' % app_name
        return

    containers = app.list_containers(limit=None)
    version_dict = {}
    for c in containers:
        if not c:
            continue
        version_dict.setdefault((c.version, c.host), []).append(c)
    for (version, host), cs in version_dict.iteritems():
        cids = [c.id for c in cs]
        task_props = {'container_ids': cids}
        task = Task.create(TASK_REMOVE, version, host, task_props)
        remove_containers.apply_async(
            args=(task.id, cids, False), task_id='task:%s' % task.id
        )
        print task
    print 'done, waiting...'


if __name__ == '__main__':
    app_name = sys.argv[-1]
    clean_app(app_name)
