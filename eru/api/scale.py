# coding: utf-8

from flask import abort

from eru.models import App

from .bp import create_api_blueprint


bp = create_api_blueprint('scale', __name__, url_prefix='/api/scale')


@bp.route('/<name>/<version>/info')
def touch_version_scale_info(name, version):
    app = App.get_by_name(name)
    if not app:
        abort(404, 'App %s not found' % name)
    v = app.get_version(version)
    if not v:
        abort(404, 'Version %s not found' % version)
    containers = v.containers.limit(1).all()
    if not containers:
        abort(404, 'Not deployed')
    container = containers[0]
    return {
        'group': container.host.group.name,
        'pod': container.host.pod.name,
        'ncore': len(container.cores.all())
    }
