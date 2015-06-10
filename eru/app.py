#!/usr/bin/python
#coding:utf-8

from flask import Flask, request, g
from werkzeug.utils import import_string
from gunicorn.app.wsgiapp import WSGIApplication

from eru.common.settings import (ERU_BIND, ERU_WORKERS,
        ERU_TIMEOUT, ERU_WORKER_CLASS, ERU_DAEMON)
from eru.async import make_celery
from eru.models import db
from eru.log import init_logging

blueprints = (
    'app',
    'container',
    'deploy',
    'host',
    'network',
    'pod',
    'version',
    'resource',
    'sys',
    'scale',
    'task',
    'websockets',
)
exts = (db, )

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

    @app.before_request
    def init_global_vars():
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)

    return app, celery

app, celery = create_app_with_celery()

def main():

    class Eru(WSGIApplication):

        def init(self, parser, opts, args):
            bind = opts.bind and opts.bind[0] or ERU_BIND
            return {
                'bind': bind,
                'daemon': opts.daemon or ERU_DAEMON,
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
