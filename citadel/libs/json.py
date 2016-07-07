# coding:utf-8

from __future__ import absolute_import

import json
from decimal import Decimal
from datetime import datetime
from functools import wraps
from flask import Response


class Jsonized(object):

    _raw = {}

    def to_dict(self):
        return self._raw


class JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Jsonized):
            return obj.to_dict()
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, Decimal):
            return float(obj)
        return super(JSONEncoder, self).default(obj)


def jsonize(f):
    @wraps(f)
    def _(*args, **kwargs):
        r = f(*args, **kwargs)
        data, code = r if isinstance(r, tuple) else (r, 200)
        return Response(json.dumps(data, cls=JSONEncoder), status=code, mimetype='application/json')
    return _
