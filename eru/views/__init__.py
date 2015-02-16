#!/usr/bin/python
# encoding: UTF-8

from eru.views.sys import sys
from eru.views.deploy import deploy
from eru.views.container import container


def init_views(app):
    app.register_blueprint(sys)
    app.register_blueprint(deploy)
    app.register_blueprint(container)

