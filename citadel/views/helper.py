# -*- coding: utf-8 -*-
import collections
from functools import wraps

from flask import g, abort
from humanfriendly import parse_size

from citadel.config import DEFAULT_ZONE
from citadel.models.app import AppUserRelation, Release, App
from citadel.models.env import Environment
from citadel.models.loadbalance import ELBInstance
from citadel.rpc import get_core


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


def make_deploy_options(release, combo_name=None, podname=None, nodename='', entrypoint=None, cpu_quota=1, count=1, memory='512MB', networks=(), envname='', extra_env='', extra_args='', debug=False):
    """
    :param release: citadel.models.app.Release instance
    :param combo_name: str, should appear in release.specs.combos
    :param nodename: str, if empty string, eru-core will choose node for ya
    :param entrypoint: str, should appear in release.specs.entrypoints
    :param cpu_quota: Number
    :param count: int, number of containers to deploy, default to 1
    :param memory: str or Number, string will be converted to Number using parse_size
    :param networks: str, tuple of str, dict, this could be a single network name, or a tuple/list of network names
    :param envname: str, Environment name
    :param extra_env: str or list of str, if str, should be 'FOO=1;BAR=2;', if list, should be ['FOO=1', 'BAR=2']
    :param extra_args: what the fuck is this?
    :param debug: bool, cheers
    """
    appname = release.name
    if combo_name:
        combo = release.specs.combos[combo_name]
        zone = combo.zone
        podname = combo.podname
        nodename = combo.nodename
        entrypoint = combo.entrypoint
        envname = combo.envname
        env = Environment.get_by_app_and_env(appname, envname)
        # combo.extra_env is dict, sorry...
        extra_env = combo.extra_env
        env_vars = env and env.to_env_vars() or []
        env_vars.extend(['='.join([k, v]) for k, v in extra_env.iteritems()])
        cpu_quota = combo.cpu
        memory = combo.memory_str
        # user can override count in combo
        count = max(combo.count, count or 1)
        networks = combo.networks
    else:
        try:
            zone = g.zone
        except AttributeError:
            zone = DEFAULT_ZONE

        env = Environment.get_by_app_and_env(appname, envname)
        env_vars = env and env.to_env_vars() or []
        if isinstance(extra_env, basestring):
            env_vars.extend(extra_env.strip().split(';'))
        elif isinstance(extra_env, list):
            env_vars.extend(extra_env)

    if isinstance(networks, basestring):
        networks ={networks: ''}
    elif isinstance(networks, collections.Sequence):
        networks = {network_name: '' for network_name in networks}

    if isinstance(memory, basestring):
        memory = parse_size(memory, binary=True)

    deploy_options = {
        'specs': release.specs_text,
        'appname': appname,
        'image': release.image,
        'zone': zone,
        'podname': podname,
        'nodename': nodename,
        'entrypoint': entrypoint,
        'cpu_quota': float(cpu_quota),
        'count': int(count),
        'memory': memory,
        'networks': networks,
        'env': env_vars,
        'raw': release.raw,
        'extra_args': extra_args,
        'debug': debug,
    }
    return deploy_options


def bp_get_balancer(id):
    elb = ELBInstance.get(id)
    if not elb:
        abort(404, 'ELB %s not found' % id)
    return elb


def get_nodes_for_first_pod(pods):
    """取一个pods列表里的第一个pod的nodes.
    场景很简单啊, 因为是页面渲染,
    第一次返回页面的时候需要一些默认值,
    默认的节点当然就是第一个pod的节点了..."""
    if not pods:
        return []
    return get_core(g.zone).get_pod_nodes(pods[0].name)


def get_networks_for_first_pod(pods):
    if not pods:
        return []
    return get_core(g.zone).get_pod_networks(pods[0].name)


def need_admin(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            abort(401)
        if not g.user.privilege:
            abort(403, 'Only for admin')
        return f(*args, **kwargs)
    return _


def make_kibana_url(appname=None, ident=None, entrypoint=None):
    if not appname:
        return 'BAD_URL'
    if ident:
        return 'http://kibana.ricebook.net/app/logtrail#/?q=name:{}%20%26%26%20ident:{}&h=All&t=Now&_g=()'.format(appname, ident)
    if entrypoint:
        return 'http://kibana.ricebook.net/app/logtrail#/?q=name:{}%20%26%26%20entrypoint:{}&h=All&t=Now&_g=()'.format(appname, entrypoint)
