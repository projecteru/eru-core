#!/usr/bin/python
#coding:utf-8

import requests
from flask import Blueprint, request, jsonify, abort

from eru.common import code
from eru.queries import group, pod, host

sys = Blueprint('sys', __name__, url_prefix='/sys')

@sys.route('/')
def index():
    return 'sys control'

@sys.route('/create/group', methods=['PUT', ])
def create_group():
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(code.HTTP_BAD_REQUEST)
    if not group.create_group(data['name'], data.get('description', '')):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/create/pod', methods=['PUT', ])
def create_pod():
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(code.HTTP_BAD_REQUEST)
    if not pod.create_pod(data['name'], data.get('description', "")):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/assign/group/<name>', methods=['PUT', ])
def assign_pod(name):
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(code.HTTP_BAD_REQUEST)
    if not group.assign_pod(name, data.get('name', '')):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/create/host/<name>', methods=['PUT', ])
def create_host(name):
    data = request.get_json()
    if not data or not data.get('addr', None):
        abort(code.HTTP_BAD_REQUEST)
    addr = data['addr']
    url = 'http://%s/info' % addr
    r = requests.get(url)
    if r.status_code != 200:
        abort(r.status_code)
    data = r.json()
    if not host.create_host(name, addr, data['Name'], data['ID'], data['NCPU'], data['MemTotal']):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/assign/host/<addr>', methods=['PUT', ])
def assign_group(addr):
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(code.HTTP_BAD_REQUEST)
    if not host.assign_group(data['name'], addr):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/cpu/<name>/<int:need>', methods=['GET', ])
def get_group_max_containers(name, need):
    ret = group.get_group_max_containers(name, need)
    if ret < 0:
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK, data=ret)

