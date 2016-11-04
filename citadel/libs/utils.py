# -*- coding: utf-8 -*-
import requests
import logging
import re
import types
from functools import wraps, partial
from threading import Thread

from etcd import EtcdException
from flask import session
from gitlab import GitlabError

from citadel.config import NOTBOT_SENDMSG_URL, LOGGER_NAME


logger = logging.getLogger(LOGGER_NAME)


def with_appcontext(f):
    @wraps(f)
    def _(*args, **kwargs):
        from citadel import flask_app
        with flask_app.app_context():
            return f(*args, **kwargs)
    return _


class ContextThread(Thread):
    """
    配置了app的thread, 可以直接执行需要appcontext的函数.
    需要实现execute方法来执行.
    """
    def execute(self):
        raise NotImplementedError('Need to implement execute method')

    def run(self):
        return with_appcontext(self.execute)()


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


_UNIT = re.compile(r'^(\d+)([kKmMgG][bB])$')
_UNIT_DICT = {
    'kb': 1024,
    'mb': 1024 * 1024,
    'gb': 1024 * 1024 * 1024,
}


def to_number(memory):
    """把字符串的内存转成数字.
    可以是纯数字, 纯数字的字符串, 也可以是带单位的字符串.
    如果出错会返回负数, 让部署的时候出错.
    因为0是不限制, 不能便宜了出错的容器..."""
    if isinstance(memory, (types.IntType, types.LongType)):
        return memory
    if isinstance(memory, basestring) and memory.isdigit():
        return int(memory)

    r = _UNIT.match(memory)
    if not r:
        return -1

    number = r.group(1)
    unit = r.group(2).lower()
    return int(number) * _UNIT_DICT.get(unit, -1)


def notbot_sendmsg(to, content, subject='Citadel message'):
    if not all([to, content]):
        return
    try:
        res = requests.post(NOTBOT_SENDMSG_URL, {'to': to, 'content': content, subject: subject})
    except:
        logger.error('Send notbot msg failed, got code %s, response %s', res.status_code, res.rext)
        return
    return res
