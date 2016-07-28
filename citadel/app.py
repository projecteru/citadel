# coding: utf-8
from flask import g, session, abort, Flask, request
from werkzeug.utils import import_string

from citadel.ext import db, mako
from citadel.libs.datastructure import DateConverter
from citadel.models.user import get_current_user
from citadel.sentry import SentryCollector


blueprints = [
    'index',
    'app',
    'user',
    'ajax',
    'admin',
    'loadbalance',
]

api_blueprints = [
    'app',
    'pod',
    'container',
    'action',
    'network',
    'mimiron',
]


def create_app():
    app = Flask(__name__, static_url_path='/citadel/static')
    app.url_map.converters['date'] = DateConverter
    app.config.from_object('citadel.config')
    app.secret_key = app.config['SECRET_KEY']

    app.url_map.strict_slashes = False

    db.init_app(app)
    mako.init_app(app)

    debug = app.config['DEBUG']

    if not debug:
        sentry = SentryCollector(dsn=app.config['SENTRY_DSN'])
        sentry.init_app(app)

    def init_sso_users():
        g.user = get_current_user() if 'sso' in session or debug else None
        if g.user is None:
            session.pop('id', None)
            session.pop('name', None)
            session.pop('sso', None)

        if not g.user:
            abort(401)

    def init_global_vars():
        g.websocket = request.environ.get('wsgi.websocket')
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)

    for bp_name in blueprints:
        bp = import_string('%s.views.%s:bp' % (__package__, bp_name))
        bp.before_request(init_global_vars)
        bp.before_request(init_sso_users)
        app.register_blueprint(bp)

    for bp_name in api_blueprints:
        bp = import_string('%s.api.v1.%s:bp' % (__package__, bp_name))
        bp.before_request(init_global_vars)
        app.register_blueprint(bp)

    return app
