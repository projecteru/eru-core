#!/usr/bin/python
#coding:utf-8

from celery import Celery
from eru.common.settings import CELERY_FORCE_ROOT

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    # patch celery for flask
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask

    if CELERY_FORCE_ROOT:
        from celery import platforms
        platforms.C_FORCE_ROOT = True

    return celery
