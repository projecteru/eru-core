#!/usr/bin/python
#coding:utf-8
import os
from setuptools import setup, find_packages
from eru import __VERSION__

# package meta info
NAME = "eru"
VERSION = __VERSION__
DESCRIPTION = "Eru, the god"
AUTHOR = "CMGS"
AUTHOR_EMAIL = "ilskdw@gmail.com"
LICENSE = "BSD"
URL = "http://git.hunantv.com"
KEYWORDS = "docker influxdb mysql"

ENTRY_POINTS = {
    'console_scripts':['eru=eru.app:main',]
}

INSTALL_REQUIRES = [
    'influxdb',
    'python-etcd',
    'MySQL-python',
    'PyYAML',
    'requests',
    'paramiko',
    'Flask-Testing',
]

here = os.path.abspath(os.path.dirname(__file__))

def read_long_description(filename):
    path = os.path.join(here, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return ""

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=read_long_description('README.rst'),
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    url=URL,
    keywords=KEYWORDS,
    packages = find_packages(exclude=['tests.*', 'tests', 'examples.*', 'examples']),
    install_package_data=True,
    zip_safe=False,
    entry_points=ENTRY_POINTS,
    install_requires=INSTALL_REQUIRES,
)

