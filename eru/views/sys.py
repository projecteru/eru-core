#!/usr/bin/python
#coding:utf-8

import requests
from flask import Blueprint, request, jsonify, abort

from eru.common import code
from eru.queries import group, pod, host
from eru.views.utils import check_request_json

sys = Blueprint('sys', __name__, url_prefix='/sys')

@sys.route('/')
def index():
    return 'sys control'

@sys.route('/create/group', methods=['PUT', ])
@check_request_json('name', code.HTTP_BAD_REQUEST)
def create_group():
    data = request.get_json()
    if not group.create_group(data['name'], data.get('description', '')):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/create/pod', methods=['PUT', ])
@check_request_json('name', code.HTTP_BAD_REQUEST)
def create_pod():
    data = request.get_json()
    if not pod.create_pod(data['name'], data.get('description', "")):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/assign/group/<name>', methods=['PUT', ])
@check_request_json('name', code.HTTP_BAD_REQUEST)
def assign_pod(name):
    data = request.get_json()
    if not group.assign_pod(name, data.get('name', '')):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/create/host/<name>', methods=['PUT', ])
@check_request_json('addr', code.HTTP_BAD_REQUEST)
def create_host(name):
    data = request.get_json()
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
@check_request_json('name', code.HTTP_BAD_REQUEST)
def assign_group(addr):
    data = request.get_json()
    if not host.assign_group(data['name'], addr):
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK), code.HTTP_CREATED

@sys.route('/cpu/<name>/<int:need>', methods=['GET', ])
def get_group_max_containers(name, need):
    ret = group.get_group_max_containers(name, need)
    if ret < 0:
        abort(code.HTTP_BAD_REQUEST)
    return jsonify(msg=code.OK, data=ret)

