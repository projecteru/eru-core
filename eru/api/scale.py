# coding: utf-8

from flask import Blueprint

from eru import consts
from eru.models import App
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException

bp = Blueprint('scale', __name__, url_prefix='/api/scale')

@bp.route('/<name>/<version>/info')
@jsonify
def touch_version_scale_info(name, version):
    app = App.get_by_name(name)
    if not app:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'App %s not found' % name)
    v = app.get_version(version)
    if not v:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Version %s not found' % version)
    containers = v.containers.limit(1).all()
    if not containers:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Not deployed')
    container = containers[0]
    return {
        'group': container.host.group.name,
        'pod': container.host.pod.name,
        'ncore': len(container.cores.all())
    }
