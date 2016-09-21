# coding: utf-8
from functools import wraps

from flask import abort, g

from citadel.models.app import App, Release, AppUserRelation
from citadel.models.loadbalance import ELBInstance
from citadel.rpc import core


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


def bp_get_balancer(id):
    elb = ELBInstance.get(id)
    if not elb:
        abort(404, 'ELB %s not found' % id)
    return elb


def bp_get_balancer_by_name(name):
    elbs = ELBInstance.get_by_name(name)
    if not elbs:
        abort(404, "No ELB named {}".format(name))
    return elbs


def get_nodes_for_first_pod(pods):
    """取一个pods列表里的第一个pod的nodes.
    场景很简单啊, 因为是页面渲染,
    第一次返回页面的时候需要一些默认值,
    默认的节点当然就是第一个pod的节点了..."""
    if not pods:
        return []
    return core.get_pod_nodes(pods[0].name)


def need_admin(f):
    @wraps(f)
    def _(*args, **kwargs):
        if not g.user:
            abort(401)
        if not g.user.privilege:
            abort(403, 'Only for admin')
        return f(*args, **kwargs)
    return _
