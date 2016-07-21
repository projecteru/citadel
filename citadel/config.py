# coding: utf-8

from smart_getenv import getenv


DEBUG = getenv('DEBUG', default=False, type=bool)
SERVER_NAME = getenv('SERVER_NAME')
SENTRY_DSN = getenv('SENTRY_DSN', default='')
SECRET_KEY = getenv('SECRET_KEY', default='testsecretkey')

MAKO_DEFAULT_FILTERS = ['unicode', 'h']
MAKO_TRANSLATE_EXCEPTIONS = False

GRPC_HOST = getenv('GRPC_HOST', default='127.0.0.1')
GRPC_PORT = getenv('GRPC_PORT', default=5001, type=int)

SQLALCHEMY_DATABASE_URI = getenv('SQLALCHEMY_DATABASE_URI', default='mysql://root:@localhost:3306/citadel')
SQLALCHEMY_TRACK_MODIFICATIONS = getenv('SQLALCHEMY_TRACK_MODIFICATIONS', default=True, type=bool)

REDIS_URL = getenv('REDIS_URL', default='redis://127.0.0.1:6379/0')
ETCD_URL = getenv('ETCD_URL', default='etcd://127.0.0.1:2379')
GITLAB_URL = getenv('GITLAB_URL', default='http://gitlab.ricebook.net')
GITLAB_PRIVATE_TOKEN = getenv('GITLAB_PRIVATE_TOKEN', default='')

OAUTH2_BASE_URL = getenv('OAUTH2_BASE_URL', default='')
OAUTH2_CLIENT_ID = getenv('OAUTH2_CLIENT_ID', default='')
OAUTH2_CLIENT_SECRET = getenv('OAUTH2_CLIENT_SECRET', default='')
OAUTH2_ACCESS_TOKEN_URL = getenv('OAUTH2_ACCESS_TOKEN_URL', default='')
OAUTH2_AUTHORIZE_URL = getenv('OAUTH2_AUTHORIZE_URL', default='')

MFS_LOG_FILE_PATH = getenv('MFS_LOG_FILE_PATH', default='/mnt/mfs/logs/eru/{app_name}/{entrypoint}/{dt}.log')
ELB_SHA = getenv('ELB_SHA', default='').split(',')
ELB_APP_NAME = getenv('ELB_APP_NAME', default='erulb')
ELB_REPO = getenv('ELB_REPO', default='git@gitlab.ricebook.net:tonic/pathlb.git')


try:
    from .local_config import *
except ImportError:
    pass
