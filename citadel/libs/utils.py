# coding:utf-8

from flask import session
from datetime import datetime
from functools import wraps
from werkzeug.routing import BaseConverter, ValidationError


def with_appcontext(f):
    @wraps(f)
    def _(*args, **kwargs):
        from citadel.app import create_app
        app = create_app()
        with app.app_context():
            return f(*args, **kwargs)
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
