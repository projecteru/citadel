# coding: utf-8

from citadel.ext import sso
from citadel.config import DEBUG


_DEBUG_USER_DICT = {
    'id': 10056,
    'name': 'liuyifu',
    'real_name': 'timfeirg',
    'email': 'test@test.com',
    'privilege': 1,
    'token': 'token',
    'pubkey': '',
}


def get_current_user():
    if DEBUG:
        return User.from_dict(_DEBUG_USER_DICT)

    resp = sso.get('me')
    return User.from_dict(resp.data)


def get_user(identifier):
    if DEBUG:
        return User.from_dict(_DEBUG_USER_DICT)

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

    @classmethod
    def from_dict(cls, info):
        if not info or not isinstance(info, dict):
            return None
        return cls(info['id'], info['name'], info['email'], info['real_name'],
                   info['privilege'], info.get('token', ''), info.get('pubkey', ''))

    @classmethod
    def get(cls, id):
        return get_user(id)
