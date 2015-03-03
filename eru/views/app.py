# coding: utf-8

import logging
from flask import Blueprint, request, abort

from eru.models import App
from eru.utils.views import jsonify, check_request_json


bp = Blueprint('app', __name__, url_prefix='/api/app')
logger = logging.getLogger(__name__)


@bp.route('/<name>', methods=['GET', ])
@jsonify()
def get_app(name):
    app = App.get_by_name(name)
    if not app:
        abort(404)
    return app


@bp.route('/<name>/<version>', methods=['GET', ])
@jsonify()
def get_version(name, version):
    app = App.get_by_name(name)
    if not app:
        abort(404)

    v = app.get_version(version)
    if not v:
        abort(404)
    return v


@bp.route('/register/', methods=['POST', ])
@check_request_json(['name', 'version', 'git', 'token', 'appyaml'])
@jsonify()
def register_app_version():
    data = request.get_json()
    name = data['name']
    version = data['version']

    app = App.get_or_create(name, data['git'], data['token'])
    if not app:
        logger.error('app create failed')
        abort(400)

    v = app.add_version(version)
    if not v:
        logger.error('version create failed')
        abort(400)

    appconfig = v.appconfig
    appconfig.update(**data['appyaml'])
    appconfig.save()
    logger.info('app version successfully created')
    return {'r': 0, 'msg': 'ok'}


@bp.route('/<name>/env/', methods=['PUT', ])
@check_request_json('env')
@jsonify()
def set_app_env(name):
    app = App.get_by_name(name)
    if not app:
        logger.error('app not found, env set ignored')
        abort(400)

    data = request.get_json()
    env = data.pop('env')
    envconfig = app.get_resource_config(env)
    envconfig.update(**data)
    envconfig.save()
    return {'r': 0, 'msg': 'ok'}


@bp.route('/<name>/env/', methods=['GET', ])
@jsonify()
def list_app_env(name):
    app = App.get_by_name(name)
    if not app:
        logger.error('app not found, env set ignored')
        abort(400)

    envconfig = app.get_resource_config(request.args['env'])
    return {'r': 0, 'msg': 'ok', 'data': envconfig.to_env_dict()}


@bp.errorhandler(404)
@bp.errorhandler(400)
@jsonify()
def not_found_handler(exception):
    return {'r':1, 'msg': str(exception.code)}

