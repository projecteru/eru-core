# coding: utf-8
import pytest

from eru.app import create_app_with_celery
from eru.models import db
from eru.redis_client import rds


@pytest.fixture
def app(request):
    app, _ = create_app_with_celery()
    app.config['TESTING'] = True

    ctx = app.app_context()
    ctx.push()

    def tear_down():
        ctx.pop()

    request.addfinalizer(tear_down)
    return app


@pytest.yield_fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_db(request, app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost:3306/erutest'
    db.create_all()

    def tear_down():
        db.session.remove()
        db.drop_all()
        rds.flushall()

    request.addfinalizer(tear_down)

