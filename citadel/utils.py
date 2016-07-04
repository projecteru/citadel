# coding:utf-8

import json
from datetime import datetime
from decimal import Decimal
from functools import wraps

from flask import session, Response
from werkzeug.routing import BaseConverter, ValidationError


def with_appcontext(f):
    @wraps(f)
    def _(*args, **kwargs):
        from karazhan.app import create_app
        app = create_app()
        with app.app_context():
            return f(*args, **kwargs)
    return _


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


def handle_exception(exceptions, default=None):
    def _handle_exception(f):
        @wraps(f)
        def _(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions:
                if callable(default):
                    return default()
                return default
        return _
    return _handle_exception


def login_user(user):
    session['id'] = user.id
    session['name'] = user.name


class DateConverter(BaseConverter):
    """Extracts a ISO8601 date from the path and validates it."""

    regex = r'\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return value.strftime('%Y-%m-%d')
