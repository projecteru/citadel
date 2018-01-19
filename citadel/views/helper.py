# -*- coding: utf-8 -*-
from flask import g, abort
from functools import wraps
from urllib.parse import urlencode

from citadel.models.app import AppUserRelation, Release, App


def bp_get_app(appname):
    app = App.get_by_name(appname)
    if not app:
        abort(404, 'App %s not found' % appname)

    if not AppUserRelation.user_permitted_to_app(g.user.id, appname) and not g.user.privilege:
        abort(403, 'You are not permitted to view this app, declare permitted_users in app.yaml')

    return app


def bp_get_release(appname, sha):
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(404, 'Release %s, %s not found' % (appname, sha))

    if not AppUserRelation.user_permitted_to_app(g.user.id, appname) and not g.user.privilege:
        abort(403, 'You are not permitted to view this app, declare permitted_users in app.yaml')

    return release


def need_admin(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            abort(401)
        if not g.user.privilege:
            abort(403, 'Only for admin')
        return f(*args, **kwargs)
    return _


def make_kibana_url(appname=None, ident=None, entrypoint=None, domain=None):
    """
    >>> make_kibana_url(domain='open.seriousapps.cn/cart')
    'http://kibana.ricebook.net/app/kibana?#/discover?_g=%28%29&_a=%28columns%3A%21%28_source%29%2Cindex%3A%27rsyslog-nginx-%2A%27%2Cinterval%3Aauto%2Cquery%3A%28query_string%3A%28analyze_wildcard%3A%21t%2Cquery%3A%27host%3Aopen.seriousapps.cn+%26%26+uri%3A%5C%2Fcart%5C%2F%2A%27%29%29%2Csort%3A%21%28rsyslog_ts%2Cdesc%29%29'

    >>> make_kibana_url(domain='notbot.intra.ricebook.net')
    'http://kibana.ricebook.net/app/kibana?#/discover?_g=%28%29&_a=%28columns%3A%21%28_source%29%2Cindex%3A%27rsyslog-nginx-%2A%27%2Cinterval%3Aauto%2Cquery%3A%28query_string%3A%28analyze_wildcard%3A%21t%2Cquery%3A%27host%3Anotbot.intra.ricebook.net%27%29%29%2Csort%3A%21%28rsyslog_ts%2Cdesc%29%29'
    """
    if domain:
        domain = domain.rstrip('/')
        if '/' in domain:
            host, path = domain.split('/', 1)
            query = 'host:{} && uri:\/{}\/*'.format(host, path.replace('/', '\/'))
        else:
            query = 'host:{}'.format(domain)

        params = {
            '_g': '()',
            '_a': "(columns:!(_source),index:'rsyslog-nginx-*',interval:auto,query:(query_string:(analyze_wildcard:!t,query:'{}')),sort:!(rsyslog_ts,desc))".format(query),
        }
        return "http://kibana.ricebook.net/app/kibana?#/discover?" + urlencode(params)
    if not appname:
        return 'BAD_URL'
    if ident:
        return 'http://kibana.ricebook.net/app/logtrail#/?q=name:{}%20%26%26%20ident:{}&h=All&t=Now&_g=()'.format(appname, ident)
    if entrypoint:
        return 'http://kibana.ricebook.net/app/logtrail#/?q=name:{}%20%26%26%20entrypoint:{}&h=All&t=Now&_g=()'.format(appname, entrypoint)
