#!/usr/bin/python
# encoding: UTF-8

from eru.views.sys import sys

def init_views(app):
    app.register_blueprint(sys)

