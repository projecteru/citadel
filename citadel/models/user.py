# -*- coding: utf-8 -*-
from flask import session

from citadel.config import FAKE_USER, DEBUG
from citadel.ext import sso
from citadel.libs.cache import cache, ONE_DAY


def get_current_user():
    if 'sso' in session:
        resp = sso.get('me')
        return User.from_dict(resp.data)
    return None


@cache(ttl=ONE_DAY)
def get_user(identifier):
    if not identifier:
        return None
    if DEBUG:
        return User.from_dict(FAKE_USER)
    resp = sso.get('user/%s' % identifier)
    return resp.data and User.from_dict(resp.data) or None


def get_users(start=0, limit=20, q=None):
    if DEBUG:
        return [User.from_dict(FAKE_USER)]

    data = {'start': start, 'limit': limit}
    if q:
        data.update({'q': q})

    resp = sso.get('users', data)
    return [User.from_dict(d) for d in resp.data if d]


class User:

    def __init__(self, id, name, email, real_name, privilege, token='', pubkey=''):
        self.id = id
        self.name = name
        self.email = email
        self.real_name = real_name
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
