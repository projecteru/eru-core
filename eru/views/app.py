# coding: utf-8

import inspect
import logging

from flask import Blueprint, request
from werkzeug.utils import import_string

from eru.models import App
from eru.common import code
from eru.common.settings import RESOURCES
from eru.utils.views import (jsonify, check_request_json,
        check_request_args, EruAbortException)


bp = Blueprint('app', __name__, url_prefix='/api/app')
logger = logging.getLogger(__name__)


@bp.route('/<name>', methods=['GET', ])
@jsonify()
def get_app(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'App %s not found' % name)
    return app


@bp.route('/<name>/<version>', methods=['GET', ])
@jsonify()
def get_version(name, version):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'App %s not found' % name)

    v = app.get_version(version)
    if not v:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Version %s not found' % version)
    return v


@bp.route('/register/', methods=['POST', ])
@check_request_json(['name', 'version', 'git', 'token', 'appyaml'])
@jsonify()
def register_app_version():
    data = request.get_json()
    name = data['name']
    version = data['version']

    #TODO dirty data
    app = App.get_or_create(name, data['git'], data['token'])
    if not app:
        logger.error('app create failed')
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'App %s create failed' % name)

    v = app.add_version(version)
    if not v:
        logger.error('version create failed')
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Version %s create failed' % version[:7])

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
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'App %s not found, env set ignored' % name)

    data = request.get_json()
    env = data.pop('env')
    envconfig = app.get_resource_config(env)
    envconfig.update(**data)
    envconfig.save()
    return {'r': 0, 'msg': 'ok'}


@bp.route('/<name>/env/', methods=['GET', ])
@check_request_args('env')
@jsonify()
def get_app_env(name):
    app = App.get_by_name(name)
    if not app:
        logger.error('app not found, env list ignored')
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'App %s not found, env list ignored' % name)

    envconfig = app.get_resource_config(request.args['env'])
    return {'r': 0, 'msg': 'ok', 'data': envconfig.to_env_dict()}


@bp.route('/<name>/listenv', methods=['GET', ])
@jsonify()
def list_app_env(name):
    app = App.get_by_name(name)
    if not app:
        logger.error('app not found, env set ignored')
        raise EruAbortException(code.HTTP_BAD_REQUEST)

    return {'r': 0, 'msg': 'ok', 'data': app.list_resource_config()}


@bp.route('/alloc/<name>/<env>/<res_name>/<res_alias>/', methods=['POST', ])
@jsonify(code.HTTP_CREATED)
def alloc_resource(name, env, res_name, res_alias):
    app = App.get_by_name(name)
    if not app:
        logger.error('app not found, allocation ignored')
        raise EruAbortException(code.HTTP_NOT_FOUND)

    r = RESOURCES.get(res_name)
    if not r:
        raise EruAbortException(code.HTTP_NOT_FOUND, '%s doesn\'t exist' % res_name)

    envconfig = app.get_resource_config(env)
    if envconfig.get(res_alias):
        raise EruAbortException(code.HTTP_CONFLICT, '%s already in env' % res_alias)

    try:
        mod = import_string(r)
        args = inspect.getargspec(mod.alloc)
        data = request.get_json()
        if set(data.iterkeys()) >= set(args.args[1:]):
            raise Exception()
        result = mod.alloc(**data)
        envconfig[res_alias] = result
        envconfig.save()
    except Exception, e:
        logger.exception(e)
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'Error in creating %s' % res_name)
    else:
        return {'r': 0, 'msg': 'ok', 'data': envconfig.to_dict()}


@bp.route('/<name>/containers/', methods=['GET', ])
@jsonify()
def list_app_containers(name):
    app = App.get_by_name(name)
    if not app:
        logger.error('app not found, env list ignored')
        raise EruAbortException(code.HTTP_BAD_REQUEST, 'App %s not found, env list ignored' % name)
    containers = app.containers.all()
    return {'r': 0, 'msg': 'ok', 'containers': containers}


@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r':1, 'msg': exception.msg, 'status_code': exception.code}

