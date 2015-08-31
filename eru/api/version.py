# coding: utf-8

from .bp import create_api_blueprint

bp = create_api_blueprint('version', __name__)

@bp.route('/')
def index():
    from eru import __VERSION__
    return {'r': 1}
    return 'Eru %s' % __VERSION__
