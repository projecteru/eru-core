#!/usr/bin/python
#coding:utf-8

from eru.models import App, Version

def get_app(name):
    return App.query.filter_by(name=name).first()

def get_version(ver_sha, app):
    return Version.query.filter(Version.sha == ver_sha,
                                Version.aid == app.id).first()
