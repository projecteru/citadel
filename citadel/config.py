# -*- coding: utf-8 -*-
import redis
from celery.schedules import crontab
from kombu import Queue
from smart_getenv import getenv


DEBUG = getenv('DEBUG', default=False, type=bool)
PROJECT_NAME = LOGGER_NAME = 'citadel'
SERVER_NAME = getenv('SERVER_NAME')
SENTRY_DSN = getenv('SENTRY_DSN', default='')
SECRET_KEY = getenv('SECRET_KEY', default='testsecretkey')

MAKO_DEFAULT_FILTERS = ['unicode', 'h']
MAKO_TRANSLATE_EXCEPTIONS = False

AGENT_PORT = getenv('AGENT_PORT', default=12345, type=int)
REDIS_URL = getenv('REDIS_URL', default='redis://127.0.0.1:6379/0')

DEFAULT_ZONE = 'c2'
BUILD_ZONE = 'c2'
ZONE_CONFIG = {
    'c1': {
        'ETCD_CLUSTER': (('10.10.70.31', 2379), ('10.10.65.251', 2379), ('10.10.145.201', 2379)),
        'GRPC_URL': '10.10.89.215:5001',
        'ELB_DB': 'redis://***REMOVED***:6379',
    },
    'c2': {
        'ETCD_CLUSTER': (('***REMOVED***', 2379), ('***REMOVED***', 2379), ('***REMOVED***', 2379)),
        'GRPC_URL': 'core-grpc.intra.ricebook.net:5001',
        'ELB_DB': 'redis://***REMOVED***:6379',
    },
}

SQLALCHEMY_DATABASE_URI = getenv('SQLALCHEMY_DATABASE_URI', default='mysql://root:@localhost:3306/citadel')
SQLALCHEMY_TRACK_MODIFICATIONS = getenv('SQLALCHEMY_TRACK_MODIFICATIONS', default=True, type=bool)

GITLAB_URL = getenv('GITLAB_URL', default='http://gitlab.ricebook.net')
GITLAB_API_URL = getenv('GITLAB_API_URL', default='http://gitlab.ricebook.net/api/v3')
GITLAB_PRIVATE_TOKEN = getenv('GITLAB_PRIVATE_TOKEN', default='')

OAUTH2_BASE_URL = getenv('OAUTH2_BASE_URL', default='http://sso.ricebook.net/oauth/api/')
OAUTH2_ACCESS_TOKEN_URL = getenv('OAUTH2_ACCESS_TOKEN_URL', default='http://sso.ricebook.net/oauth/token')
OAUTH2_AUTHORIZE_URL = getenv('OAUTH2_AUTHORIZE_URL', default='http://sso.ricebook.net/oauth/authorize')
OAUTH2_CLIENT_ID = getenv('OAUTH2_CLIENT_ID', default='')
OAUTH2_CLIENT_SECRET = getenv('OAUTH2_CLIENT_SECRET', default='')
AUTH_AUTHORIZE_URL = getenv('AUTH_AUTHORIZE_URL', default='http://sso.ricebook.net/auth/profile')
AUTH_GET_USER_URL = getenv('AUTH_GET_USER_URL', default='http://sso.ricebook.net/auth/user')

ELB_APP_NAME = getenv('ELB_APP_NAME', default='erulb')
ELB_BACKEND_NAME_DELIMITER = getenv('ELB_BACKEND_NAME_DELIMITER', default='___')
ELB_POD_NAME = getenv('ELB_POD_NAME', default='elb')

HUB_ADDRESS = getenv('HUB_ADDRESS', default='hub.ricebook.net')

REDIS_POD_NAME = getenv('REDIS_POD_NAME', default='redis')

NOTBOT_SENDMSG_URL = getenv('NOTBOT_SENDMSG_URL', default='http://notbot.intra.ricebook.net/api/sendmsg.peter')

TASK_PUBSUB_CHANNEL = 'citadel:task:{task_id}:pubsub'
# send this to mark EOF of stream message
# TODO: ugly
TASK_PUBSUB_EOF = 'CELERY_TASK_DONE:{task_id}'

try:
    from .local_config import *
except ImportError:
    pass

# redis pod is managed by cerberus, elb pod is managed by views.loadbalance
IGNORE_PODS = {REDIS_POD_NAME, ELB_POD_NAME}

# celery config
timezone = 'Asia/Shanghai'
broker_url = getenv('CELERY_BROKER_URL', default=REDIS_URL)
result_backend = getenv('CELERY_RESULT_BACKEND', default=REDIS_URL)
# if a task isn't acknownledged in 10s, redeliver to another worker
broker_transport_options = {'visibility_timeout': 10}
# rds.nova is used by so many other services, must not interfere
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
        'task': 'citadel.tasks.clean_images',
        'schedule': crontab(hour='4'),
    },
}

# flask-session settings
SESSION_USE_SIGNER = True
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.Redis.from_url(REDIS_URL)
SESSION_KEY_PREFIX = '{}:session:'.format(PROJECT_NAME)
