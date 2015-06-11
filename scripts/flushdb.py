# coding: utf-8

import sys

from eru.app import create_app_with_celery
from eru.models import db

def flushdb(app):
    with app.app_context():
        db.drop_all()
        db.create_all()

if __name__ == '__main__':
    app, _ = create_app_with_celery()
    if app.config['MYSQL_HOST'] in ('127.0.0.1', 'localhost') or '--force' in sys.argv:
        flushdb(app)
    else:
        print 'you are not doing this on your own host,'
        print 'if sure, add --force to run this script'
