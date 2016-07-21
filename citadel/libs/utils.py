# coding:utf-8
from functools import wraps, partial

from etcd import EtcdException
from flask import session
from gitlab import GitlabError


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


handle_etcd_exception = partial(handle_exception, (EtcdException, ValueError, KeyError))
handle_gitlab_exception = partial(handle_exception, (GitlabError,))


def login_user(user):
    session['id'] = user.id
    session['name'] = user.name


def make_unicode(s):
    try:
        return s.decode('utf-8')
    except:
        return s
