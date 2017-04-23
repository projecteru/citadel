# coding: utf-8
import requests
from flask import abort, session, request
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError

from citadel.config import DEBUG, AUTH_AUTHORIZE_URL, AUTH_GET_USER_URL
from citadel.ext import sso
from citadel.libs.cache import cache, ONE_DAY
from citadel.libs.utils import memoize, logger


_DEBUG_USER_DICT = {
    'id': 10056,
    'name': 'liuyifu',
    'real_name': 'timfeirg',
    'email': 'test@test.com',
    'privilege': 1,
    'token': 'token',
    'pubkey': '',
}


@cache(ttl=ONE_DAY)
def get_current_user_via_auth(token):
    try:
        headers = {'X-Neptulon-Token': token}
        resp = requests.get(AUTH_AUTHORIZE_URL, headers=headers, timeout=5)
    except (ConnectTimeout, ConnectionError, ReadTimeout):
        abort(408, 'error when getting user from neptulon')

    status_code = resp.status_code
    if status_code != 200:
        logger.warn('Neptulon error during citadel request %s: headers %s, code %s, body %s', request, headers, status_code, resp.text)
        return None

    return User.from_dict(resp.json())


@cache(ttl=ONE_DAY)
def get_user_via_auth(token, identifier):
    try:
        headers = {'X-Neptulon-Token': token}
        params = {'identifier': identifier}
        resp = requests.get(AUTH_GET_USER_URL,
                            headers=headers,
                            params=params,
                            timeout=5)
    except (ConnectTimeout, ConnectionError, ReadTimeout):
        abort(408, 'error when getting user from neptulon')

    status_code = resp.status_code
    if status_code != 200:
        logger.warn('Neptulon error during citadel request %s: headers %s, params %s, code %s, body %s', request, headers, params, status_code, resp.text)
        return None

    return User.from_dict(resp.json())


def get_current_user():
    token = request.headers.get('X-Neptulon-Token') or request.values.get('X-Neptulon-Token')
    if token:
        return get_current_user_via_auth(token)
    if 'sso' in session:
        resp = sso.get('me')
        return User.from_dict(resp.data)
    return None


@memoize
def get_user(identifier):
    if DEBUG:
        return User.from_dict(_DEBUG_USER_DICT)

    token = request.headers.get('X-Neptulon-Token') or request.values.get('X-Neptulon-Token')
    if token:
        return get_user_via_auth(token, identifier)
    resp = sso.get('user/%s' % identifier)
    return resp.data and User.from_dict(resp.data) or None


def get_users(start=0, limit=20, q=None):
    if DEBUG:
        return [User.from_dict(_DEBUG_USER_DICT)]

    data = {'start': start, 'limit': limit}
    if q:
        data.update({'q': q})

    resp = sso.get('users', data)
    return [User.from_dict(d) for d in resp.data if d]


class User(object):

    def __init__(self, id, name, email, realname, privilege, token='', pubkey=''):
        self.id = id
        self.name = name
        self.email = email
        self.realname = realname
        self.privilege = privilege
        self.token = token
        self.pubkey = pubkey

    def __str__(self):
        return '{class_} {u.name}'.format(
            class_=self.__class__,
            u=self,
        )

    def __hash__(self):
        return hash((self.__class__, self.id))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    @classmethod
    def from_dict(cls, info):
        if not info or not isinstance(info, dict):
            return None
        return cls(info['id'], info['name'], info['email'], info['real_name'],
                   info['privilege'], info.get('token', ''), info.get('pubkey', ''))

    @classmethod
    def get(cls, id):
        return get_user(id)
