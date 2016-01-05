# coding:utf-8

import logging
from flask import Flask, request, g
from werkzeug.utils import import_string
from gunicorn.app.wsgiapp import WSGIApplication

from eru.config import (
    ERU_BIND,
    ERU_DAEMON,
    ERU_TIMEOUT,
    ERU_WORKERS,
    ERU_WORKER_CLASS,
)
from eru.async import make_celery
from eru.models import db

blueprints = (
    'app',
    'container',
    'deploy',
    'host',
    'network',
    'pod',
    'version',
    'task',
    'websockets',
)
exts = (db, )


LOG_FORMAT = '[%(asctime)s] [%(process)d] [%(levelname)s] [%(name)s] %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S %z'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)


def create_app_with_celery(static_url_path=None):
    app = Flask('eru', static_url_path=static_url_path)
    app.config.from_object('eru.config')

    # should be initialized before other imports
    celery = make_celery(app)

    for ext in exts:
        ext.init_app(app)

    for bp in blueprints:
        import_name = '%s.api.%s:bp' % (__package__, bp)
        app.register_blueprint(import_string(import_name))

    @app.before_request
    def init_global_vars():
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)

    return app, celery


app, celery = create_app_with_celery()


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
            'reload': bool(opts.reload),
        }

    def load(self):
        return app


def main():
    Eru().run()


if __name__ == '__main__':
    main()
