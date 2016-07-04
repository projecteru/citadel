# coding: utf-8
from functools import partial, wraps

from flask import Blueprint, jsonify, abort, g
from flask_mako import render_template

from citadel.utils import jsonize


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


def create_ajax_blueprint(name, import_name, url_prefix=None):
    bp = Blueprint(name, import_name, url_prefix=url_prefix)

    def _error_hanlder(error):
        return jsonify({'error': error.description}), error.code

    for code in ERROR_CODES:
        bp.errorhandler(code)(_error_hanlder)

    patch_blueprint_route(bp)
    return bp


def patch_blueprint_route(bp):
    origin_route = bp.route

    def patched_route(self, rule, **options):
        def decorator(f):
            origin_route(rule, **options)(jsonize(f))
        return decorator

    bp.route = partial(patched_route, bp)


def create_page_blueprint(name, import_name, url_prefix=None):
    bp = Blueprint(name, import_name, url_prefix=url_prefix)

    def _error_hanlder(error):
        return render_template('/error/%s.mako' % error.code)

    for code in ERROR_CODES:
        bp.errorhandler(code)(_error_hanlder)

    return bp
