# coding: utf-8

from redis import Redis
from etcd import Client
from flask_sqlalchemy import SQLAlchemy
from flask_oauthlib.client import OAuth
from flask_mako import MakoTemplates
from gitlab import Gitlab

from urlparse import urlparse

from citadel.rpc.client import CoreRPC
from citadel.config import (
    REDIS_URL,
    ETCD_URL,
    OAUTH2_BASE_URL,
    OAUTH2_CLIENT_ID,
    OAUTH2_CLIENT_SECRET,
    OAUTH2_ACCESS_TOKEN_URL,
    OAUTH2_AUTHORIZE_URL,
    GITLAB_URL,
    GITLAB_PRIVATE_TOKEN,
    GRPC_HOST,
    GRPC_PORT,
)


def get_etcd_client(url):
    r = urlparse(url)
    return Client(r.hostname, r.port)


db = SQLAlchemy()
mako = MakoTemplates()
oauth = OAuth()
rds = Redis.from_url(REDIS_URL)
etcd = get_etcd_client(ETCD_URL)
core = CoreRPC(GRPC_HOST, GRPC_PORT)

sso = oauth.remote_app(
    'sso',
    consumer_key=OAUTH2_CLIENT_ID,
    consumer_secret=OAUTH2_CLIENT_SECRET,
    request_token_params={'scope': 'email'},
    base_url=OAUTH2_BASE_URL,
    request_token_url=None,
    access_token_url=OAUTH2_ACCESS_TOKEN_URL,
    authorize_url=OAUTH2_AUTHORIZE_URL,
)

gitlab = Gitlab(GITLAB_URL, private_token=GITLAB_PRIVATE_TOKEN)
