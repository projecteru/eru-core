#!/usr/bin/python
#coding:utf-8

from eru.models import App, Version

def get_app(name):
    return App.query.filter_by(name=name).first()

def get_version(ver, app):
    return Version.query.filter(Version.app.has(id=app.id)).first()

