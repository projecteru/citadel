# -*- coding: utf-8 -*-

import redis
from celery.schedules import crontab
from datetime import timedelta
from kombu import Queue
from mock import MagicMock
from smart_getenv import getenv


DEBUG = getenv('DEBUG', default=True, type=bool)
FAKE_USER = MagicMock(
    id=12345,
    name='timfeirg',
    email='timfeirg@ricebook.com',
    privileged=1,
)
FAKE_USER.name = 'timfeirg'  # ...

PROJECT_NAME = LOGGER_NAME = 'citadel'
SERVER_NAME = getenv('SERVER_NAME', default='citadel.ricebook.net')
SENTRY_DSN = getenv('SENTRY_DSN', default='')
SECRET_KEY = getenv('SECRET_KEY', default='testsecretkey')

MAKO_DEFAULT_FILTERS = ['unicode', 'h']
MAKO_TRANSLATE_EXCEPTIONS = False

AGENT_PORT = getenv('AGENT_PORT', default=12345, type=int)
REDIS_URL = getenv('REDIS_URL', default='redis://127.0.0.1:6379/0')

CORE_DEPLOY_INFO_PATH = '/eru-core/deploy'
DEFAULT_ZONE = 'test-zone'
BUILD_ZONE = 'test-zone'
ZONE_CONFIG = {
    'test-zone': {
        'ETCD_CLUSTER': (('127.0.0.1', 2379), ),
        'CORE_URL': '127.0.0.1:5001',
        'ELB_DB': 'redis://127.0.0.1:6379',
    },
}

SQLALCHEMY_DATABASE_URI = getenv('SQLALCHEMY_DATABASE_URI', default='mysql+pymysql://root:@localhost:3306/citadeltest')
SQLALCHEMY_TRACK_MODIFICATIONS = getenv('SQLALCHEMY_TRACK_MODIFICATIONS', default=True, type=bool)

OAUTH_APP_NAME = 'github'
GITHUB_CLIENT_KEY = 'ce5e0d16937ca68c3f53'
GITHUB_CLIENT_SECRET = 'e3f80ef7abf3446e63063bfdb211414824c923fe'
GITHUB_CLIENT_KWARGS = {'scope': 'user:email'}
OAUTH_CLIENT_CACHE_TYPE = 'redis'

ELB_APP_NAME = getenv('ELB_APP_NAME', default='erulb3')
ELB_BACKEND_NAME_DELIMITER = getenv('ELB_BACKEND_NAME_DELIMITER', default='___')
ELB_POD_NAME = getenv('ELB_POD_NAME', default='elb')
CITADEL_HEALTH_CHECK_STATS_KEY = 'citadel:health'

REDIS_POD_NAME = getenv('REDIS_POD_NAME', default='redis')

NOTBOT_SENDMSG_URL = getenv('NOTBOT_SENDMSG_URL', default='http://notbot.intra.ricebook.net/api/sendmsg.peter')

TASK_PUBSUB_CHANNEL = 'citadel:task:{task_id}:pubsub'
# send this to mark EOF of stream message
# TODO: ugly
TASK_PUBSUB_EOF = 'CELERY_TASK_DONE:{task_id}'

# celery config
timezone = 'Asia/Shanghai'
broker_url = getenv('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
result_backend = getenv('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0')
broker_transport_options = {'visibility_timeout': 10}
task_default_queue = PROJECT_NAME
task_queues = (
    Queue(PROJECT_NAME, routing_key=PROJECT_NAME),
)
task_default_exchange = PROJECT_NAME
task_default_routing_key = PROJECT_NAME
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json', 'pickle']
beat_schedule = {
    'record-health': {
        'task': 'citadel.tasks.record_health_status',
        'schedule': timedelta(seconds=20),
    },
    'tackle-beat': {
        'task': 'citadel.tasks.trigger_tackle_routine',
        'schedule': timedelta(seconds=30),
        # task message expire in 1 second to prevent flooding citadel with
        # unnecessary eru-tackle tasks
        'options': {'expires': 1},
    },
    # FIXME:
    # 'crontab': {
    #     'task': 'citadel.tasks.trigger_scheduled_task',
    #     'schedule': crontab(minute='*'),
    #     'options': {'expires': 60},
    # },
    'backup': {
        'task': 'citadel.tasks.trigger_backup',
        'schedule': crontab(minute=0, hour=6),
    },
}

try:
    from .local_config import *
except ImportError:
    pass

# flask-session settings
SESSION_USE_SIGNER = True
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.Redis.from_url(REDIS_URL)
SESSION_KEY_PREFIX = '{}:session:'.format(PROJECT_NAME)
PERMANENT_SESSION_LIFETIME = timedelta(days=5)

# flask cache settings
CACHE_REDIS_URL = REDIS_URL

# citadel-tackle config
CITADEL_TACKLE_EXPRESSION_KEY = 'citadel:tackle:expression:{}-{}-{}'
CITADEL_TACKLE_TASK_THROTTLING_KEY = 'citadel:tackle:throttle:{id_}:{strategy}'
GRAPHITE_QUERY_FROM = getenv('GRAPHITE_QUERY_FROM', default='-3min')
GRAPHITE_QUERY_STRING_PATTERN = 'group(eru.{app_name}.*.*.*.*.*, eru.{app_name}.*.*.*.*.*.*.*.*)'
GRAPHITE_TARGET_PATTERN = 'eru.{app_name}.{version}.{entrypoint}.{hostname}.{container_id}.{metric}'
GRAPHITE_DATA_SERIES_NAME_TEMPLATE = '{app_name}-{cid}'
