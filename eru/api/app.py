# coding: utf-8

from flask import Blueprint, request, g, current_app

from eru import consts
from eru.models import App
from eru.models.appconfig import verify_appconfig
from eru.utils.decorator import jsonify, check_request_json, check_request_args
from eru.utils.exception import EruAbortException

bp = Blueprint('app', __name__, url_prefix='/api/app')

@bp.route('/<name>/', methods=['GET', ])
@jsonify
def get_app(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'App %s not found' % name)
    return app

@bp.route('/<name>/<version>/', methods=['GET', ])
@jsonify
def get_version(name, version):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'App %s not found' % name)

    v = app.get_version(version)
    if not v:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Version %s not found' % version)
    return v

@bp.route('/register/', methods=['POST', ])
@jsonify
@check_request_json(['name', 'version', 'git', 'token', 'appyaml'])
def register_app_version():
    data = request.get_json()
    name = data['name']

    version = data['version']

    app = App.get_or_create(name, data['git'], data['token'])
    if not app:
        current_app.logger.error('App create failed. (name=%s, version=%s)', name, version[:7])
        raise EruAbortException(consts.HTTP_BAD_REQUEST,
                'App %s create failed, maybe token duplicated' % name)

    v = app.add_version(version)
    if not v:
        current_app.logger.error('Version create failed. (name=%s, version=%s)', name, version[:7])
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'Version %s create failed' % version[:7])

    appyaml = data['appyaml']
    try:
        verify_appconfig(appyaml)
    except (ValueError, KeyError) as e:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, e.message)

    appconfig = v.appconfig
    appconfig.update(**appyaml)
    appconfig.save()
    current_app.logger.info('App-Version created. (name=%s, version=%s)', name, version[:7])
    return {'r': 0, 'msg': 'ok'}

@bp.route('/<name>/env/', methods=['PUT', ])
@jsonify
@check_request_json('env')
def set_app_env(name):
    data = request.get_json()
    env = data.pop('env')

    app = App.get_by_name(name)
    if not app:
        current_app.logger.error('App (name=%s) not found, env (env=%s) set ignored.', name, env)
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, env set ignored' % name)

    envconfig = app.get_resource_config(env)
    envconfig.update(**data)
    envconfig.save()
    current_app.logger.error('App (name=%s) set env (env=%s) values done', name, env)
    return {'r': 0, 'msg': 'ok'}

@bp.route('/<name>/env/', methods=['GET', ])
@jsonify
@check_request_args('env')
def get_app_env(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, env list ignored' % name)

    envconfig = app.get_resource_config(request.args['env'])
    return {'r': 0, 'msg': 'ok', 'data': envconfig.to_env_dict()}

@bp.route('/<name>/listenv/', methods=['GET', ])
@jsonify
def list_app_env(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST)
    return {'r': 0, 'msg': 'ok', 'data': app.list_resource_config()}

@bp.route('/<name>/containers/', methods=['GET', ])
@jsonify
def list_app_containers(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, container list ignored' % name)
    return {'r': 0, 'msg': 'ok', 'containers': app.list_containers(g.start, g.limit)}

@bp.route('/<name>/tasks/', methods=['GET', ])
@jsonify
def list_app_tasks(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, container list ignored' % name)
    return {'r': 0, 'msg': 'ok', 'tasks': app.list_tasks(g.start, g.limit)}

@bp.route('/<name>/versions/', methods=['GET', ])
@jsonify
def list_app_versions(name):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, version list ignored' % name)
    return {'r': 0, 'msg': 'ok', 'versions': app.list_versions(g.start, g.limit)}

@bp.route('/<name>/<version>/containers/', methods=['GET', ])
@jsonify
def list_version_containers(name, version):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, env list ignored' % name)
    v = app.get_version(version)
    if not v:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Version %s not found' % version)
    return {'r': 0, 'msg': 'ok', 'containers': v.list_containers(g.start, g.limit)}

@bp.route('/<name>/<version>/tasks/', methods=['GET', ])
@jsonify
def list_version_tasks(name, version):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_BAD_REQUEST, 'App %s not found, env list ignored' % name)
    v = app.get_version(version)
    if not v:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Version %s not found' % version)
    return {'r': 0, 'msg': 'ok', 'tasks': v.list_tasks(g.start, g.limit)}
