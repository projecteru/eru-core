# coding: utf-8

import json
import inspect
import functools
from datetime import datetime
from flask import request, Response

from eru import consts
from eru.clients import rds
from eru.models.base import Base
from eru.utils.exception import EruAbortException

def redis_lock(fmt):
    def _redis_lock(f):
        @functools.wraps(f)
        def _(*args, **kwargs):
            ags = inspect.getargspec(f)
            kw = dict(zip(ags.args, args))
            kw.update(kwargs)
            with rds.lock(fmt.format(**kw)):
                return f(*args, **kwargs)
        return _
    return _redis_lock

def check_request_json(keys, abort_code=consts.HTTP_BAD_REQUEST, abort_msg=''):
    if not isinstance(keys, list):
        keys = [keys, ]
    def deco(function):
        @functools.wraps(function)
        def _(*args, **kwargs):
            data = request.get_json()
            if not (data and all((k in data) for k in keys)):
                raise EruAbortException(abort_code, abort_msg)
            return function(*args, **kwargs)
        return _
    return deco

def check_request_args(keys, abort_code=consts.HTTP_BAD_REQUEST, abort_msg=''):
    if not isinstance(keys, list):
        keys = [keys, ]
    def deco(function):
        @functools.wraps(function)
        def _(*args, **kwargs):
            if not all((k in request.args) for k in keys):
                raise EruAbortException(abort_code, abort_msg)
            return function(*args, **kwargs)
        return _
    return deco

class EruJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Base):
            return obj.to_dict()
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(EruJSONEncoder, self).default(obj)

def jsonify(f):
    @functools.wraps(f)
    def _(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
            if isinstance(r, tuple):
                code, data = r
            else:
                code, data = 200, r
        except EruAbortException as e:
            code, data = e.code, {'error': e.message}
        return Response(json.dumps(data, cls=EruJSONEncoder), status=code, mimetype='application/json')
    return _
