# -*- coding: utf-8 -*-
import json
import logging
from functools import wraps, partial

import requests
from etcd import EtcdException
from flask import session
from gitlab import GitlabError

from citadel.config import NOTBOT_SENDMSG_URL, LOGGER_NAME, DEBUG
from citadel.libs.jsonutils import JSONEncoder


logger = logging.getLogger(LOGGER_NAME)

login_handler = logging.FileHandler('/var/tmp/citadel-login.log')
login_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
login_logger = logging.getLogger('login')
login_logger.addHandler(login_handler)
login_logger.setLevel(logging.INFO)


def with_appcontext(f):
    @wraps(f)
    def _(*args, **kwargs):
        from citadel.app import create_app
        app = create_app()
        with app.app_context():
            return f(*args, **kwargs)
    return _


def handle_exception(exceptions, default=None):
    def _handle_exception(f):
        @wraps(f)
        def _(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions as e:
                logger.error('Call %s error: %s', f.func_name, e)
                if callable(default):
                    return default()
                return default
        return _
    return _handle_exception


handle_etcd_exception = partial(handle_exception, (EtcdException, ValueError, KeyError))
handle_gitlab_exception = partial(handle_exception, (GitlabError,))


def login_user(user):
    session['id'] = user.id
    session['name'] = user.name


def make_unicode(s):
    try:
        return s.decode('utf-8')
    except:
        return s


def shorten_sentence(s, length=88):
    if len(s) > length:
        return s[:length]
    return s


def normalize_domain(domain):
    """保留第一级的path, 并且去掉最后的/"""
    if '/' not in domain:
        return domain

    r = domain.split('/', 2)
    if len(r) == 2:
        domain, path = r
        if path:
            return '/'.join([domain, path])
        return domain
    else:
        domain = r[0]
        path = r[1]
        return '/'.join([domain, path])


def parse_domain(domain):
    s = domain.split('/')
    if len(s) == 1:
        domain, location = s[0], ''
    else:
        domain, location = s[:2]
    return domain, '/' + location


def notbot_sendmsg(to, content, subject='Citadel message'):
    to = to.strip(';')
    if not all([to, content]):
        return
    if DEBUG:
        logger.debug('Sending notbot message to %s, content: %s', to, content)
        return
    try:
        res = requests.post(NOTBOT_SENDMSG_URL, {'to': to, 'content': content, subject: subject})
    except:
        logger.error('Send notbot msg failed, got code %s, response %s', res.status_code, res.rext)
        return
    return res


def make_shell_env(env_content):
    return '\n'.join('export {}=\'{}\''.format(k, v) for k, v in env_content)


def memoize(f):
    """ Memoization decorator for a function taking one or more arguments. """
    class memodict(dict):
        def __getitem__(self, *key):
            return dict.__getitem__(self, key)

        def __missing__(self, key):
            res = f(*key)
            if res:
                self[key] = res

            return res

    return memodict().__getitem__


def make_sentence_json(message):
    msg = json.dumps({'type': 'sentence', 'message': message}, cls=JSONEncoder)
    return msg + '\n'
