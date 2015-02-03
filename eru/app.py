#!/usr/bin/python
#coding:utf-8

import logging
import settings
from flask import Flask

from eru.models import init_db
from eru.views import init_views

def init_logging():
    args = {'level': logging.INFO}
    if settings.DEBUG:
        args = {'level': logging.DEBUG}
    args['format'] = '%(levelname)s:%(asctime)s:%(message)s'
    logging.basicConfig(**args)

def init_mysql(app):
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

#TODO init influxdb etcd

def create_app(static_url_path=None):
    app = Flask('eru', static_url_path=static_url_path)
    app.debug = settings.DEBUG

    init_logging()
    init_mysql(app)
    init_views(app)

    return app

app = create_app()

@app.route("/")
def index():
    from eru import __VERSION__
    return 'Eru %s' % __VERSION__

def main():
    app.run()

