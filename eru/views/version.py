# coding: utf-8

from flask import Blueprint


bp = Blueprint('version', __name__, url_prefix='')


@bp.route('/')
def index():
    from eru import __VERSION__
    return 'Eru %s' % __VERSION__

