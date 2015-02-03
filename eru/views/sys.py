#!/usr/bin/python
#coding:utf-8

import requests
from flask import Blueprint, request, jsonify, abort

from eru.queries import groups, pods, hosts

sys = Blueprint('sys', __name__, url_prefix='/sys')

@sys.route('/')
def index():
    return 'sys control'

@sys.route('/create/group', methods=['PUT', ])
def create_group():
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(400)
    if not groups.create_group(data['name'], data.get('description', '')):
        abort(400)
    return jsonify(msg='ok'), 201

@sys.route('/create/pod', methods=['PUT', ])
def create_pod():
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(400)
    if not pods.create_pod(data['name'], data.get('description', "")):
        abort(400)
    return jsonify(msg='ok'), 201

@sys.route('/assign/group/<name>', methods=['PUT', ])
def assign_pod(name):
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(400)
    if not groups.assign_pod(name, data.get('name', '')):
        abort(400)
    return jsonify(msg='ok'), 201

@sys.route('/create/host/<name>', methods=['PUT', ])
def create_host(name):
    data = request.get_json()
    if not data or not data.get('addr', None):
        abort(400)
    addr = data['addr']
    url = 'http://%s/info' % addr
    r = requests.get(url)
    if r.status_code != 200:
        abort(r.status_code)
    data = r.json()
    if not hosts.create_host(name, addr, data['Name'], data['ID'], data['NCPU'], data['MemTotal']):
        abort(400)
    return jsonify(msg='ok'), 201

@sys.route('/assign/host/<addr>', methods=['PUT', ])
def assign_group(addr):
    data = request.get_json()
    if not data or not data.get('name', None):
        abort(400)
    if not hosts.assign_group(data['name'], addr):
        abort(400)
    return jsonify(msg='ok'), 201

