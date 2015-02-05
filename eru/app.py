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

def create_db(app):
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
        CELERY_ENABLE_UTC = settings.CELERY_ENABLE_UTC,
        CELERY_TIMEZONE = settings.CELERY_TIMEZONE,
        CELERY_BROKER_URL = settings.CELERY_BROKER_URL,
        CELERY_RESULT_BACKEND = settings.CELERY_RESULT_BACKEND,
        CELERY_ACCEPT_CONTENT = settings.CELERY_ACCEPT_CONTENT,
        CELERY_REDIS_MAX_CONNECTIONS = settings.CELERY_REDIS_MAX_CONNECTIONS,
        CELERY_TASK_RESULT_EXPIRES = settings.CELERY_TASK_RESULT_EXPIRES,
        CELERY_TRACK_STARTED = settings.CELERY_TRACK_STARTED,
        CELERY_SEND_TASK_ERROR_EMAILS = settings.CELERY_SEND_TASK_ERROR_EMAILS,
        ADMINS = settings.ADMINS,
        SERVER_EMAIL = settings.SERVER_EMAIL,
        EMAIL_HOST = settings.EMAIL_HOST,
        EMAIL_PORT = settings.EMAIL_PORT,
        EMAIL_HOST_USER = settings.EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD,
        EMAIL_USE_SSL = settings.EMAIL_USE_SSL,
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
    create_db(app)
    create_views(app)

    return app, celery

app, celery = create_app()

@app.route("/")
def index():
    from eru import __VERSION__
    return 'Eru %s' % __VERSION__

def main():
    app.run()

