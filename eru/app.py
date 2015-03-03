#!/usr/bin/python
#coding:utf-8

import logging
from flask import Flask
from gunicorn.app.wsgiapp import WSGIApplication
from werkzeug.utils import import_string

from eru.common.settings import ERU_BIND, ERU_WORKERS,\
        ERU_TIMEOUT, ERU_WORKER_CLASS
from eru.async import make_celery
from eru.models import db
from eru.utils.views import EruJSONEncoder


blueprints = ('version', 'sys', 'deploy', 'container', 'app', )
exts = (db, )


def init_logging(app):
    args = {
        'level': logging.DEBUG if app.debug else logging.INFO,
        'format': '%(levelname)s:%(asctime)s:%(message)s',
    }
    logging.basicConfig(**args)


def create_app_with_celery(static_url_path=None):
    app = Flask('eru', static_url_path=static_url_path)
    app.config.from_object('eru.common.settings')

    # should be initialized before other imports
    celery = make_celery(app)

    init_logging(app)

    for ext in exts:
        ext.init_app(app)

    for bp in blueprints:
        import_name = '%s.views.%s:bp' % (__package__, bp)
        app.register_blueprint(import_string(import_name))

    return app, celery


app, celery = create_app_with_celery()


def main():

    class Eru(WSGIApplication):

        def init(self, parser, opts, args):
            bind = opts.bind and opts.bind[0] or ERU_BIND
            return {
                'bind': bind,
                'workers': opts.workers or ERU_WORKERS,
                'timeout': opts.timeout or ERU_TIMEOUT,
                'worker_class': opts.worker_class or ERU_WORKER_CLASS,
                'pidfile': opts.pidfile,
            }

        def load(self):
            return app

    Eru().run()


if __name__ == '__main__':
    main()

