# coding: utf-8

from flask import Flask, g, request, session
from werkzeug.utils import import_string

from citadel.config import DEBUG, SENTRY_DSN
from citadel.ext import db, mako
from citadel.sentry import SentryCollector
from citadel.models.user import get_current_user
# from citadel.utils import DateConverter


blueprints = [
    'core',
]


def create_app():
    app = Flask(__name__, static_url_path='/citadel/static')
    # app.url_map.converters['date'] = DateConverter
    app.config.from_object('citadel.config')
    app.secret_key = app.config['SECRET_KEY']

    app.url_map.strict_slashes = False

    db.init_app(app)
    mako.init_app(app)

    if not DEBUG:
        sentry = SentryCollector(dsn=SENTRY_DSN)
        sentry.init_app(app)

    for bp in blueprints:
        import_name = '%s.views.%s:bp' % (__package__, bp)
        app.register_blueprint(import_string(import_name))

    @app.before_request
    def init_global_vars():
        g.user = get_current_user() if 'sso' in session or DEBUG else None
        if g.user is None:
            session.pop('id', None)
            session.pop('name', None)
            session.pop('sso', None)

        g.websocket = request.environ.get('wsgi.websocket', None)
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)

    return app
