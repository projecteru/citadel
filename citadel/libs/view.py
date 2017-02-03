# coding: utf-8
import os
from functools import partial

from flask import Blueprint, jsonify
from flask_mako import render_template

from citadel.libs.jsonutils import jsonize


ERROR_CODES = [400, 401, 403, 404, 408]
DEFAULT_RETURN_VALUE = {'error': None}


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
        return render_template('/error/%s.mako' % error.code, err=error)

    for code in ERROR_CODES:
        bp.errorhandler(code)(_error_hanlder)

    return bp


class URLPrefixError(Exception):
    pass


def create_api_blueprint(name, import_name, url_prefix=None, version='v1', jsonize=True):
    """
    幺蛾子, 就是因为flask写API挂路由太累了, 搞了这么个东西.
    会把url_prefix挂到/api/:version/下.
    比如url_prefix是test, 那么route全部在/api/v1/test下
    """
    if url_prefix and url_prefix.startswith('/'):
        raise URLPrefixError('url_prefix ("%s") must not start with /' % url_prefix)
    if version.startswith('/'):
        raise URLPrefixError('version ("%s") must not start with /' % version)

    bp_name = '_'.join([name, version])
    bp_url_prefix = '/api/' + version
    if url_prefix:
        bp_url_prefix = os.path.join(bp_url_prefix, url_prefix)
    bp = Blueprint(bp_name, import_name, url_prefix=bp_url_prefix)

    def _error_hanlder(error):
        return jsonify({'error': error.description}), error.code

    for code in ERROR_CODES:
        bp.errorhandler(code)(_error_hanlder)

    # 如果不需要自动帮忙jsonize, 就不要
    # 可能的场景比如返回一个stream
    if jsonize:
        patch_blueprint_route(bp)
    return bp
