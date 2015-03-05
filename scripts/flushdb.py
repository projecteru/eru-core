# coding: utf-8

from eru.app import create_app_with_celery
from eru.models import db

if __name__ == '__main__':
    app, _ = create_app_with_celery()
    with app.app_context():
        db.drop_all()
        db.create_all()

