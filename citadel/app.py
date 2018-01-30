# -*- coding: utf-8 -*-

import json
import logging
from celery import Celery, Task
from flask import url_for, jsonify, g, session, Flask, request, redirect, current_app
from raven.contrib.flask import Sentry
from werkzeug.utils import import_string

from citadel.config import TASK_PUBSUB_CHANNEL, DEBUG, SENTRY_DSN, TASK_PUBSUB_EOF, DEFAULT_ZONE, FAKE_USER
from citadel.ext import rds, sess, db, mako, cache, sockets, oauth
from citadel.libs.datastructure import DateConverter
from citadel.libs.jsonutils import JSONEncoder
from citadel.libs.utils import notbot_sendmsg
from citadel.models.user import get_current_user, User


if DEBUG:
    loglevel = logging.DEBUG
else:
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('etcd').setLevel(logging.CRITICAL)
    loglevel = logging.INFO

logging.basicConfig(level=loglevel, format='[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s @ %(lineno)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S %z')

api_blueprints = [
    'app',
    'pod',
    'container',
    'elb',
    'user',
]

ANONYMOUS_PATHS = [
    '/user',
    '/health-check',
]


def anonymous_path(path):
    for p in ANONYMOUS_PATHS:
        if path.startswith(p):
            return True
    return False


def make_celery(app):
    celery = Celery(app.import_name)
    celery.config_from_object('citadel.config')

    class EruGRPCTask(Task):

        abstract = True

        def stream_output(self, data, task_id=None):
            channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id or self.request.id)
            rds.publish(channel_name, json.dumps(data, cls=JSONEncoder))

        def on_success(self, retval, task_id, args, kwargs):
            channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id)
            rds.publish(channel_name, TASK_PUBSUB_EOF.format(task_id=task_id))

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            channel_name = TASK_PUBSUB_CHANNEL.format(task_id=task_id)
            failure_msg = {'error': str(exc), 'args': args, 'kwargs': kwargs}
            rds.publish(channel_name, json.dumps(failure_msg, cls=JSONEncoder))
            rds.publish(channel_name, TASK_PUBSUB_EOF.format(task_id=task_id))
            msg = 'Citadel task {}:\nargs\n```\n{}\n```\nkwargs:\n```\n{}\n```\nerror message:\n```\n{}\n```'.format(self.name, args, kwargs, str(exc))
            notbot_sendmsg('#platform', msg)

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super(EruGRPCTask, self).__call__(*args, **kwargs)

    celery.Task = EruGRPCTask
    celery.autodiscover_tasks(['citadel'])
    return celery


def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')
    app.url_map.converters['date'] = DateConverter
    app.config.from_object('citadel.config')
    app.secret_key = app.config['SECRET_KEY']

    app.url_map.strict_slashes = False

    make_celery(app)
    db.init_app(app)
    oauth.init_app(app)
    mako.init_app(app)
    cache.init_app(app)
    sess.init_app(app)
    sockets.init_app(app)

    if not DEBUG:
        sentry = Sentry(dsn=SENTRY_DSN)
        sentry.init_app(app)

    for bp_name in api_blueprints:
        bp = import_string('%s.api.%s:bp' % (__package__, bp_name))
        app.register_blueprint(bp)

    # action APIs are all websockets
    from citadel.api.action import ws
    sockets.register_blueprint(ws)

    @app.before_request
    def init_global_vars():
        g.start = request.args.get('start', type=int, default=0)
        g.limit = request.args.get('limit', type=int, default=20)
        g.zone = session.get('zone') or request.values.get('zone') or DEFAULT_ZONE

        if current_app.config['DEBUG']:
            g.user = User(**FAKE_USER)
        else:
            g.user = get_current_user()

        if not g.user and not anonymous_path(request.path):
            return redirect(url_for('user.login'))

    @app.errorhandler(422)
    def handle_unprocessable_entity(err):
        # webargs attaches additional metadata to the `data` attribute
        exc = getattr(err, 'exc')
        if exc:
            # Get validations from the ValidationError object
            messages = exc.messages
        else:
            messages = ['Invalid request']
        return jsonify({
            'messages': messages,
        }), 422

    return app


app = create_app()
celery = make_celery(app)
