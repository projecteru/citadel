# -*- coding: utf-8 -*-

from authlib.client.apps import github
from authlib.flask.client import OAuth
from etcd import Client
from flask import session
from flask_caching import Cache
from flask_mako import MakoTemplates
from flask_session import Session
from flask_sockets import Sockets
from flask_sqlalchemy import SQLAlchemy
from redis import Redis

from citadel.config import ZONE_CONFIG, REDIS_URL
from citadel.libs.utils import memoize


@memoize
def get_etcd(zone):
    cluster = ZONE_CONFIG[zone]['ETCD_CLUSTER']
    return Client(cluster, allow_reconnect=True)


db = SQLAlchemy()
mako = MakoTemplates()
sockets = Sockets()
rds = Redis.from_url(REDIS_URL)


def fetch_token(oauth_app_name):
    token_session_key = '{}-token'.format(oauth_app_name.lower())
    return session.get(token_session_key)


def update_token(oauth_app_name, token):
    token_session_key = '{}-token'.format(oauth_app_name.lower())
    session[token_session_key] = token
    # I don't think return token was necessary, but that's what the example
    # does in the docs: https://docs.authlib.org/en/latest/client/frameworks.html#cache-database
    return token


oauth = OAuth(fetch_token=fetch_token, update_token=update_token)
github.register_to(oauth)

cache = Cache(config={'CACHE_TYPE': 'redis'})
sess = Session()
