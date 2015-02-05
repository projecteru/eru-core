#!/usr/bin/python
#coding:utf-8

import logging
import settings
from flask import Flask

from eru.async import make_celery

def init_logging():
    args = {'level': logging.INFO}
    if settings.DEBUG:
        args = {'level': logging.DEBUG}
    args['format'] = '%(levelname)s:%(asctime)s:%(message)s'
    logging.basicConfig(**args)

def create_mysql(app):
    from eru.models import init_db
    dsn = 'mysql://{username}:{password}@{host}:{port}/{db}'.format(
        username = settings.MYSQL_USER,
        password = settings.MYSQL_PASSWORD,
        host = settings.MYSQL_HOST,
        port = settings.MYSQL_PORT,
        db = settings.MYSQL_DATABASE,
    )
    app.config.update(
        SQLALCHEMY_DATABASE_URI=dsn,
        SQLALCHEMY_POOL_SIZE=settings.SQLALCHEMY_POOL_SIZE,
        SQLALCHEMY_POOL_TIMEOUT=settings.SQLALCHEMY_POOL_TIMEOUT,
        SQLALCHEMY_POOL_RECYCLE=settings.SQLALCHEMY_POOL_RECYCLE,
    )
    init_db(app)

def create_celery(app):
    app.config.update(
        CELERY_BROKER_URL = settings.CELERY_BROKER_URL,
        CELERY_RESULT_BACKEND = settings.CELERY_RESULT_BACKEND,
    )

    return make_celery(app)

def create_views(app):
    from eru.views import init_views
    init_views(app)


#TODO init influxdb etcd

def create_app(static_url_path=None):
    app = Flask('eru', static_url_path=static_url_path)
    app.debug = settings.DEBUG
    celery = create_celery(app)

    init_logging()
    create_mysql(app)
    create_views(app)

    return app, celery

app, celery = create_app()

@app.route("/")
def index():
    from eru import __VERSION__
    return 'Eru %s' % __VERSION__

def main():
    app.run()

