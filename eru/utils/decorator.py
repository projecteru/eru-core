# coding: utf-8

import json
import inspect
import functools

from flask import request, Response, abort
from datetime import datetime
from decimal import Decimal

from eru.clients import rds
from eru.utils import Jsonized

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

def check_request_json(keys):
    if not isinstance(keys, list):
        keys = [keys, ]
    def deco(function):
        @functools.wraps(function)
        def _(*args, **kwargs):
            data = request.get_json()
            if not data:
                abort(400, 'did you set content-type to application/json '
                           'and request body is json serializable?')

            for k in keys:
                if k not in data:
                    abort(400, '%s must be in request body after jsonized' % k)
            return function(*args, **kwargs)
        return _
    return deco

def check_request_args(keys):
    if not isinstance(keys, list):
        keys = [keys, ]
    def deco(function):
        @functools.wraps(function)
        def _(*args, **kwargs):
            for k in keys:
                if k not in request.args:
                    abort(400, '%s must be in querystring' % k)
            return function(*args, **kwargs)
        return _
    return deco

class EruJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Jsonized):
            return obj.to_dict()
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, Decimal):
            return float(obj)
        return super(EruJSONEncoder, self).default(obj)

def jsonize(f):
    @functools.wraps(f)
    def _(*args, **kwargs):
        r = f(*args, **kwargs)
        code, data = r if isinstance(r, tuple) else (200, r)
        return Response(json.dumps(data, cls=EruJSONEncoder), status=code, mimetype='application/json')
    return _
