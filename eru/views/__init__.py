#!/usr/bin/python
# encoding: UTF-8

from eru.views.sys import sys
from eru.views.deploy import deploy

def init_views(app):
    app.register_blueprint(sys)
    app.register_blueprint(deploy)

