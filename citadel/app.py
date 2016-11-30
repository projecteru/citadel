# coding: utf-8
import json
import logging

from celery import Celery, Task
from flask import g, abort, session, Flask, request
from werkzeug.utils import import_string

from citadel.config import TASK_PUBSUB_CHANNEL, TASK_PUBSUB_EOF
from citadel.ext import rds, db, mako
from citadel.libs.datastructure import DateConverter
from citadel.libs.utils import notbot_sendmsg
from citadel.models.user import get_current_user, get_current_user_via_auth
from citadel.sentry import SentryCollector


logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s @ %(lineno)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S %z')

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

ANONYMOUS_PATHS = [
    '/user',
]


def anonymous_path(path):
    for p in ANONYMOUS_PATHS:
        if path.startswith(p):
            return True
    return False


def make_celery(app):
    celery = Celery(app.import_name)
    celery.config_from_object('citadel.celeryconfig')

    class EruGRPCTask(Task):

        abstract = True

        def on_success(self, retval, task_id, args, kwargs):
            channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id)
            rds.publish(channel_name, TASK_PUBSUB_EOF)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id)
            rds.publish(channel_name, json.dumps({'error': einfo.traceback}))
            rds.publish(channel_name, TASK_PUBSUB_EOF)
            msg = 'Deploy with args:\n```\n{}\n```\nkwargs:\n```\n{}\n```\n*EXCEPTION*:\n```\n{}\n```'.format(args, kwargs, einfo.traceback)
            notbot_sendmsg('@timfeirg', msg)

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return Task.__call__(self, *args, **kwargs)

    celery.Task = EruGRPCTask
    celery.autodiscover_tasks(['citadel'])
    return celery


def create_app():
    app = Flask(__name__, static_url_path='/citadel/static')
    app.url_map.converters['date'] = DateConverter
    app.config.from_object('citadel.config')
    app.secret_key = app.config['SECRET_KEY']
    logger = logging.getLogger(app.config['LOGGER_NAME'])

    app.url_map.strict_slashes = False

    make_celery(app)
    db.init_app(app)
    mako.init_app(app)

    debug = app.config['DEBUG']
    if debug:
        logger.setLevel(logging.DEBUG)

    if not debug:
        sentry = SentryCollector(dsn=app.config['SENTRY_DSN'])
        sentry.init_app(app)

    for bp_name in blueprints:
        bp = import_string('%s.views.%s:bp' % (__package__, bp_name))
        app.register_blueprint(bp)

    for bp_name in api_blueprints:
        bp = import_string('%s.api.v1.%s:bp' % (__package__, bp_name))
        app.register_blueprint(bp)

    @app.before_request
    def init_global_vars():
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)

        token = request.headers.get('X-Neptulon-Token', '') or request.values.get('X-Neptulon-Token')
        g.user = token and get_current_user_via_auth(token) or (get_current_user() if 'sso' in session or debug else None)

        if not g.user:
            session.pop('sso', None)
        if not g.user and not anonymous_path(request.path):
            abort(401, 'Must login')

    return app
