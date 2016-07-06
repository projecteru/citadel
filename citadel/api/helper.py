# coding: utf-8

import os
from functools import partial, wraps
from flask import Blueprint, jsonify, abort, g

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


class URLPrefixError(Exception):
    pass


def create_api_blueprint(name, import_name, url_prefix=None, version='v1'):
    if url_prefix.startswith('/'):
        raise URLPrefixError('url_prefix ("%s") must not start with /' % url_prefix)

    bp_name = '_'.join([name, version])
    bp_url_prefix = os.path.join('/api', version, url_prefix)
    bp = Blueprint(bp_name, import_name, url_prefix=bp_url_prefix)

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


class AbortDict(dict):

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            abort(400, '`%s` must be in dict' % key)
