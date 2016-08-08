# coding: utf-8

from flask import abort, g

from citadel.ext import core
from citadel.models.app import App, Release, AppUserRelation
from citadel.models.loadbalance import ELBInstance


def bp_get_app(appname):
    app = App.get_by_name(appname)
    if not app:
        abort(404, 'App %s not found' % appname)

    appnames = AppUserRelation.get_appname_by_user_id(g.user.id, limit=200)
    if appname not in appnames and not g.user.privilege:
        abort(403, 'Not permitted')
    return app


def bp_get_release(appname, sha):
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(404, 'Release %s, %s not found' % (appname, sha))

    appnames = AppUserRelation.get_appname_by_user_id(g.user.id, limit=200)
    if appname not in appnames and not g.user.privilege:
        abort(403, 'Not permitted')
    return release


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
    return core.get_pod_nodes(pods[0].name)
