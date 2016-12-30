# coding: utf-8
import redis
from kombu import Queue
from smart_getenv import getenv


DEBUG = getenv('DEBUG', default=False, type=bool)
PROJECT_NAME = LOGGER_NAME = 'citadel'
SERVER_NAME = getenv('SERVER_NAME')
SENTRY_DSN = getenv('SENTRY_DSN', default='')
SECRET_KEY = getenv('SECRET_KEY', default='testsecretkey')

MAKO_DEFAULT_FILTERS = ['unicode', 'h']
MAKO_TRANSLATE_EXCEPTIONS = False

GRPC_HOST = getenv('GRPC_HOST', default='127.0.0.1')
GRPC_PORT = getenv('GRPC_PORT', default=5001, type=int)
AGENT_PORT = getenv('AGENT_PORT', default=12345, type=int)

SQLALCHEMY_DATABASE_URI = getenv('SQLALCHEMY_DATABASE_URI', default='mysql://root:@localhost:3306/citadel')
SQLALCHEMY_TRACK_MODIFICATIONS = getenv('SQLALCHEMY_TRACK_MODIFICATIONS', default=True, type=bool)

REDIS_URL = getenv('REDIS_URL', default='redis://127.0.0.1:6379/0')
ETCD_URL = getenv('ETCD_URL', default='etcd://127.0.0.1:2379')

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

REDIS_POD_NAME = getenv('REDIS_POD_NAME', default='redis')

NOTBOT_SENDMSG_URL = getenv('NOTBOT_SENDMSG_URL', default='http://notbot.intra.ricebook.net/api/sendmsg.peter')

TASK_PUBSUB_CHANNEL = 'citadel:task:{task_id}:pubsub'
CONTAINER_DEBUG_LOG_CHANNEL = 'eru-debug:{}*'
# send this to mark EOF of stream message
# TODO: ugly
TASK_PUBSUB_EOF = 'CELERY_TASK_DONE:{task_id}'

try:
    from .local_config import *
except ImportError:
    pass

# redis pod is managed by cerberus, elb pod is managed by views.loadbalance
IGNORE_PODS = {REDIS_POD_NAME, ELB_POD_NAME}

ELB_REDIS_URL = getenv('ELB_REDIS_URL', default=REDIS_URL)

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
accept_content = ['pickle']

# flask-session settings
SESSION_USE_SIGNER = True
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.Redis.from_url(REDIS_URL)
SESSION_KEY_PREFIX = '{}:session:'.format(PROJECT_NAME)
