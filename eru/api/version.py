# coding: utf-8

from eru import __VERSION__
from .bp import create_api_blueprint


bp = create_api_blueprint('version', __name__)


@bp.route('/')
def index():
    return {'version': __VERSION__}
