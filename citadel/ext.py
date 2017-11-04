# coding: utf-8
import mapi
from etcd import Client
from flask_caching import Cache
from flask_mako import MakoTemplates
from flask_oauthlib.client import OAuth
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from redis import Redis

from citadel.config import ZONE_CONFIG, HUB_ADDRESS, REDIS_URL, OAUTH2_BASE_URL, OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET, OAUTH2_ACCESS_TOKEN_URL, OAUTH2_AUTHORIZE_URL
from citadel.libs.utils import memoize


@memoize
def get_etcd(zone):
    cluster = ZONE_CONFIG[zone]['ETCD_CLUSTER']
    return Client(cluster, allow_reconnect=True)


db = SQLAlchemy()
mako = MakoTemplates()
oauth = OAuth()
rds = Redis.from_url(REDIS_URL)

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

cache = Cache(config={'CACHE_TYPE': 'redis'})
sess = Session()
hub = mapi.MapiClient(HUB_ADDRESS, use_tls=True)
