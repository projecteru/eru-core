# coding: utf-8

import yaml
import logging
from flask import request, g, abort

from eru.models import App
from eru.models.appconfig import verify_appconfig
from eru.utils.decorator import check_request_json, check_request_args

from .bp import create_api_blueprint, DEFAULT_RETURN_VALUE

bp = create_api_blueprint('app', __name__, url_prefix='/api/app')
_log = logging.getLogger(__name__)


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
@check_request_json(['version', 'git', 'appyaml'])
def register_app_version():
    data = request.get_json()
    version = data['version']

    appyaml = data['appyaml']
    if isinstance(appyaml, basestring):
        try:
            appyaml = yaml.load(appyaml)
        except yaml.error.YAMLError:
            abort(400, 'Error in app.yaml')

    try:
        verify_appconfig(appyaml)
    except (ValueError, KeyError) as e:
        abort(400, e.message)

    name = appyaml['appname']

    app = App.get_or_create(name, data['git'])

    v = app.add_version(version)
    if not v:
        _log.error('Version create failed. (name=%s, version=%s)', name, version[:7])
        abort(400, 'Version %s create failed' % version[:7])

    appconfig = v.appconfig
    appconfig.update(**appyaml)
    appconfig.save()

    _log.info('App-Version created. (name=%s, version=%s)', name, version[:7])
    return 201, DEFAULT_RETURN_VALUE


@bp.route('/<name>/env/', methods=['PUT', 'DELETE'])
@check_request_json('env')
def set_app_env(name):
    data = request.get_json()
    env = data.pop('env')

    app = _get_app_by_name(name)
    envconfig = app.get_resource_config(env)
    if request.method == 'PUT':
        envconfig.update(**data)
        envconfig.save()
    elif request.method == 'DELETE':
        envconfig.delete()

    _log.info('App (name=%s) set env (env=%s) values done', name, env)
    return DEFAULT_RETURN_VALUE


@bp.route('/<name>/env/', methods=['GET', ])
@check_request_args('env')
def get_app_env(name):
    app = _get_app_by_name(name)
    envconfig = app.get_resource_config(request.args['env'])
    return envconfig.to_env_dict()


@bp.route('/<name>/listenv/', methods=['GET', ])
def list_app_env(name):
    app = _get_app_by_name(name)
    return app.list_resource_config()


@bp.route('/<name>/containers/', methods=['GET', ])
def list_app_containers(name):
    app = _get_app_by_name(name)
    return app.list_containers(g.start, g.limit)


@bp.route('/<name>/tasks/', methods=['GET', ])
def list_app_tasks(name):
    app = _get_app_by_name(name)
    return app.list_tasks(g.start, g.limit)


@bp.route('/<name>/versions/', methods=['GET', ])
def list_app_versions(name):
    app = _get_app_by_name(name)
    return app.list_versions(g.start, g.limit)


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
    return v.list_containers(g.start, g.limit)


@bp.route('/<name>/<version>/tasks/', methods=['GET', ])
def list_version_tasks(name, version):
    app = _get_app_by_name(name)
    v = app.get_version(version)
    if not v:
        abort(404, 'Version %s not found' % version)
    return v.list_tasks(g.start, g.limit)
