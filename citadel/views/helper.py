# coding: utf-8
from functools import wraps

from flask import Blueprint, abort, g
from flask_mako import render_template


ERROR_CODES = [400, 401, 403, 404]
DEFAULT_RETURN_VALUE = {'error': None}


def need_login(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            abort(401)
        return f(*args, **kwargs)
    return _


def need_admin(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            abort(401)
        if not g.user.privilege:
            abort(403)
        return f(*args, **kwargs)
    return _


def create_page_blueprint(name, import_name, url_prefix=None):
    bp = Blueprint(name, import_name, url_prefix=url_prefix)

    def _error_hanlder(error):
        return render_template('/error/%s.mako' % error.code)

    for code in ERROR_CODES:
        bp.errorhandler(code)(_error_hanlder)

    return bp
