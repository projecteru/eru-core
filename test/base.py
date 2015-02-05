from flask import Flask
import flask.ext.testing

from eru.models import db
from eru.views import init_views


class TestCase(flask.ext.testing.TestCase):
    def create_app(self):
        app = Flask('EruTest')
        app.config['TESTING'] = True
        db.init_app(app)
        init_views(app)
        return app

    def setUp(self):
        db.create_all()
        self.db = db

    def tearDown(self):
        db.session.remove()
        db.drop_all()
