# coding: utf-8

from flask import request, g, current_app, abort

from eru.models import App
from eru.models.appconfig import verify_appconfig
from eru.utils.decorator import check_request_json, check_request_args

from .bp import create_api_blueprint

bp = create_api_blueprint('app', __name__, url_prefix='/api/app')


def _get_app_by_name(name):
    app = App.get_by_name(name)
    if not app:
        abort(404, 'App %s not found' % name)
    return app


@bp.route('/', methods=['GET'])
def list_all_apps():
    return App.list_all(g.start, g.limit)


@bp.route('/<name>/', methods=['GET', ])
def get_app(name):
    return _get_app_by_name(name)


@bp.route('/<name>/<version>/', methods=['GET', ])
def get_version(name, version):
    app = _get_app_by_name(name)
    v = app.get_version(version)
    if not v:
        abort(404, 'Version %s not found' % version)
    return v


@bp.route('/register/', methods=['POST', ])
@check_request_json(['version', 'git', 'token', 'appyaml'])
def register_app_version():
    data = request.get_json()
    version = data['version']

    appyaml = data['appyaml']
    try:
        verify_appconfig(appyaml)
    except (ValueError, KeyError) as e:
        abort(400, e.message)

    name = appyaml['appname']

    app = App.get_or_create(name, data['git'], data['token'])
    if not app:
        current_app.logger.error('App create failed. (name=%s, version=%s)', name, version[:7])
        abort(400, 'App %s create failed, maybe token duplicated' % name)

    v = app.add_version(version)
    if not v:
        current_app.logger.error('Version create failed. (name=%s, version=%s)', name, version[:7])
        abort(400, 'Version %s create failed' % version[:7])

    appconfig = v.appconfig
    appconfig.update(**appyaml)
    appconfig.save()
    current_app.logger.info('App-Version created. (name=%s, version=%s)', name, version[:7])
    return {'r': 0, 'msg': 'ok'}


@bp.route('/<name>/env/', methods=['PUT', ])
@check_request_json('env')
def set_app_env(name):
    data = request.get_json()
    env = data.pop('env')

    app = _get_app_by_name(name)
    envconfig = app.get_resource_config(env)
    envconfig.update(**data)
    envconfig.save()
    current_app.logger.info('App (name=%s) set env (env=%s) values done', name, env)
    return {'r': 0, 'msg': 'ok'}


@bp.route('/<name>/env/', methods=['GET', ])
@check_request_args('env')
def get_app_env(name):
    app = _get_app_by_name(name)
    envconfig = app.get_resource_config(request.args['env'])
    return {'r': 0, 'msg': 'ok', 'data': envconfig.to_env_dict()}


@bp.route('/<name>/listenv/', methods=['GET', ])
def list_app_env(name):
    app = _get_app_by_name(name)
    return {'r': 0, 'msg': 'ok', 'data': app.list_resource_config()}


@bp.route('/<name>/containers/', methods=['GET', ])
def list_app_containers(name):
    app = _get_app_by_name(name)
    return {'r': 0, 'msg': 'ok', 'containers': app.list_containers(g.start, g.limit)}


@bp.route('/<name>/tasks/', methods=['GET', ])
def list_app_tasks(name):
    app = _get_app_by_name(name)
    return {'r': 0, 'msg': 'ok', 'tasks': app.list_tasks(g.start, g.limit)}


@bp.route('/<name>/versions/', methods=['GET', ])
def list_app_versions(name):
    app = _get_app_by_name(name)
    return {'r': 0, 'msg': 'ok', 'versions': app.list_versions(g.start, g.limit)}


@bp.route('/<name>/images/', methods=['GET', ])
def list_app_images(name):
    app = _get_app_by_name(name)
    return app.list_images(g.start, g.limit)


@bp.route('/<name>/<version>/containers/', methods=['GET', ])
def list_version_containers(name, version):
    app = _get_app_by_name(name)
    v = app.get_version(version)
    if not v:
        abort(404, 'Version %s not found' % version)
    return {'r': 0, 'msg': 'ok', 'containers': v.list_containers(g.start, g.limit)}


@bp.route('/<name>/<version>/tasks/', methods=['GET', ])
def list_version_tasks(name, version):
    app = _get_app_by_name(name)
    v = app.get_version(version)
    if not v:
        abort(404, 'Version %s not found' % version)
    return {'r': 0, 'msg': 'ok', 'tasks': v.list_tasks(g.start, g.limit)}
