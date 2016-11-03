# coding: utf-8
import logging

from flask import g, abort, session, Flask, request

from citadel.ext import db, mako
from citadel.libs.datastructure import DateConverter
from citadel.models.user import get_current_user, get_current_user_via_auth
from citadel.sentry import SentryCollector


logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.basicConfig(format='[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s @ %(lineno)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S %z')
ANONYMOUS_PATHS = [
    '/hook',
    '/user',
]


def anonymous_path(path):
    for p in ANONYMOUS_PATHS:
        if path.startswith(p):
            return True
    return False


flask_app = Flask(__name__, static_url_path='/citadel/static')
flask_app.url_map.converters['date'] = DateConverter
flask_app.url_map.strict_slashes = False
flask_app.config.from_object('citadel.config')
flask_app.secret_key = flask_app.config['SECRET_KEY']
logger = logging.getLogger(flask_app.config['LOGGER_NAME'])
debug = flask_app.config['DEBUG']
if debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
    sentry = SentryCollector(dsn=flask_app.config['SENTRY_DSN'])
    sentry.init_app(flask_app)

db.init_app(flask_app)
mako.init_app(flask_app)


@flask_app.before_request
def init_global_vars():
    g.start = request.args.get('start', type=int, default=0)
    g.limit = request.args.get('limit', type=int, default=20)

    token = request.headers.get('X-Neptulon-Token', '') or request.values.get('X-Neptulon-Token')
    g.user = token and get_current_user_via_auth(token) or (get_current_user() if 'sso' in session or debug else None)

    if not g.user:
        session.pop('sso', None)
    if not g.user and not anonymous_path(request.path):
        abort(401, 'Must login')


import citadel.views
import citadel.api.v1
