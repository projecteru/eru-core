# coding: utf-8

import json
from functools import wraps
from flask import request, abort, Response

def check_request_json(keys, abort_code):
    if not isinstance(keys, list):
        keys = [keys, ]
    def deco(function):
        @wraps(function)
        def _(*args, **kwargs):
            data = request.get_json()
            if not (data and all((k in data) for k in keys)):
                abort(abort_code)
            return function(*args, **kwargs)
        return _
    return deco


def jsonify(f):
    @wraps(f)
    def _(*args, **kwargs):
        r = f(*args, **kwargs)
        return r and Response(json.dumps(r), mimetype='application/json')
    return _

