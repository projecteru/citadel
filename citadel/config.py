# -*- coding: utf-8 -*-
from datetime import timedelta

import redis
from celery.schedules import crontab
from kombu import Queue
from smart_getenv import getenv


DEBUG = getenv('DEBUG', default=True, type=bool)
FAKE_USER = {
    'id': 10056,
    'name': 'liuyifu',
    'real_name': 'timfeirg',
    'email': 'test@test.com',
    'privilege': 1,
    'token': 'token',
    'pubkey': '',
}

PROJECT_NAME = LOGGER_NAME = 'citadel'
SERVER_NAME = getenv('SERVER_NAME', default='citadel.ricebook.net')
SENTRY_DSN = getenv('SENTRY_DSN', default='')
SECRET_KEY = getenv('SECRET_KEY', default='testsecretkey')

MAKO_DEFAULT_FILTERS = ['unicode', 'h']
MAKO_TRANSLATE_EXCEPTIONS = False

AGENT_PORT = getenv('AGENT_PORT', default=12345, type=int)
REDIS_URL = getenv('REDIS_URL', default='redis://127.0.0.1:6379/0')

WHEREAMI = getenv('WHEREAMI', default='c2-eru-1')
DEFAULT_ZONE = 'c2'
BUILD_ZONE = 'c1'
ZONE_CONFIG = {
    'c1': {
        'ETCD_CLUSTER': (('10.10.70.***', 2379), ('10.10.65.***', 2379), ('10.10.145.***', 2379)),
        'GRPC_URL': '10.10.89.***:5001',
        'ELB_DB': 'redis://10.215.244.17:6379',
    },
    'c2': {
        'ETCD_CLUSTER': (('10.215.242.***', 2379), ('10.215.242.***', 2379), ('10.215.242.***', 2379)),
        'GRPC_URL': '10.215.244.***:5001',
        'ELB_DB': 'redis://10.215.244.***:6379',
    },
}

SQLALCHEMY_DATABASE_URI = getenv('SQLALCHEMY_DATABASE_URI', default='mysql+pymysql://root:@localhost:3306/citadel')
SQLALCHEMY_TRACK_MODIFICATIONS = getenv('SQLALCHEMY_TRACK_MODIFICATIONS', default=True, type=bool)

OAUTH2_BASE_URL = getenv('OAUTH2_BASE_URL', default='https://sso.ricebook.net/oauth/api/')
OAUTH2_ACCESS_TOKEN_URL = getenv('OAUTH2_ACCESS_TOKEN_URL', default='https://sso.ricebook.net/oauth/token')
OAUTH2_AUTHORIZE_URL = getenv('OAUTH2_AUTHORIZE_URL', default='https://sso.ricebook.net/oauth/authorize')
OAUTH2_CLIENT_ID = getenv('OAUTH2_CLIENT_ID', default='whatever')
OAUTH2_CLIENT_SECRET = getenv('OAUTH2_CLIENT_SECRET', default='whatever')
AUTH_AUTHORIZE_URL = getenv('AUTH_AUTHORIZE_URL', default='https://sso.ricebook.net/auth/profile')
AUTH_GET_USER_URL = getenv('AUTH_GET_USER_URL', default='https://sso.ricebook.net/auth/user')

ELB_APP_NAME = getenv('ELB_APP_NAME', default='erulb3')
ELB_BACKEND_NAME_DELIMITER = getenv('ELB_BACKEND_NAME_DELIMITER', default='___')
ELB_POD_NAME = getenv('ELB_POD_NAME', default='elb')
CITADEL_HEALTH_CHECK_STATS_KEY = 'citadel:health'

# some envs are managed by eru-core, should copy from
# http://gitlab.ricebook.net/platform/core/blob/master/cluster/calcium/create_container.go#L541
UPGRADE_CONTAINER_IGNORE_ENV = {
    'ERU_NODE_IP',
    'ERU_NODE_NAME',
    'APP_NAME',
    'ERU_POD',
    'ERU_ZONE',
}

HUB_ADDRESS = getenv('HUB_ADDRESS', default='hub.ricebook.net')

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
task_serializer = 'pickle'
accept_content = ['pickle', 'json']
beat_schedule = {
    'clean-images': {
        'task': 'citadel.tasks.clean_stuff',
        'schedule': crontab(hour='4'),
    },
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
    'crontab': {
        'task': 'citadel.tasks.trigger_scheduled_task',
        'schedule': crontab(minute='*'),
        'options': {'expires': 60},
    },
    'backup': {
        'task': 'citadel.tasks.trigger_backup',
        'schedule': crontab(minute=0, hour=6),
    },
}

try:
    from .local_config import *
except ImportError:
    pass

# redis pod is managed by cerberus, elb pod is managed by views.loadbalance
IGNORE_PODS = {REDIS_POD_NAME, ELB_POD_NAME}

# flask-session settings
SESSION_USE_SIGNER = True
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.Redis.from_url(REDIS_URL)
SESSION_KEY_PREFIX = '{}:session:'.format(PROJECT_NAME)
PERMANENT_SESSION_LIFETIME = timedelta(days=2)

# flask cache settings
CACHE_REDIS_URL = REDIS_URL

# citadel-tackle config
CITADEL_TACKLE_EXPRESSION_KEY = 'citadel:tackle:expression:{}-{}-{}'
CITADEL_TACKLE_TASK_THROTTLING_KEY = 'citadel:tackle:throttle:{id_}:{strategy}'
GRAPHITE_QUERY_FROM = getenv('GRAPHITE_QUERY_FROM', default='-3min')
GRAPHITE_QUERY_STRING_PATTERN = 'group(eru.{app_name}.*.*.*.*.*, eru.{app_name}.*.*.*.*.*.*.*.*)'
GRAPHITE_TARGET_PATTERN = 'eru.{app_name}.{version}.{entrypoint}.{hostname}.{container_id}.{metric}'
GRAPHITE_DATA_SERIES_NAME_TEMPLATE = '{app_name}-{cid}'
