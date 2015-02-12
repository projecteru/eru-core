#!/usr/bin/python
#coding:utf-8

import logging
from flask import Flask
from gunicorn.app.wsgiapp import WSGIApplication

from eru.common import settings
from eru.async import make_celery


def init_logging(app):
    args = {'level': logging.INFO}
    if app.debug:
        args = {'level': logging.DEBUG}
    args['format'] = '%(levelname)s:%(asctime)s:%(message)s'
    logging.basicConfig(**args)


def create_app_with_celery(static_url_path=None):
    app = Flask('eru', static_url_path=static_url_path)
    app.config.from_object('settings')

    # should be initialized before other imports
    celery = make_celery(app)

    from eru.models import init_db
    from eru.views import init_views

    init_logging(app)
    init_db(app)
    init_views(app)

    @app.route("/")
    def index():
        from eru import __VERSION__
        return 'Eru %s' % __VERSION__

    return app, celery


app, celery = create_app_with_celery()


def main():

    class Eru(WSGIApplication):

        def init(self, parser, opts, args):
            return {
                'bind': '{0}:{1}'.format(settings.ERU_HOST, settings.ERU_PORT),
                'workers': settings.ERU_WORKERS,
            }

        def load(self):
            return app

    Eru().run()


if __name__ == '__main__':
    main()
