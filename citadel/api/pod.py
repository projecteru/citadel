# -*- coding: utf-8 -*-
from flask import g, abort

from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container
from citadel.rpc.client import get_core
from citadel.libs.view import user_require


bp = create_api_blueprint('pod', __name__, 'pod')


def _get_pod(name):
    pod = get_core(g.zone).get_pod(name)
    if not pod:
        abort(404, 'pod `%s` not found' % name)

    return pod


@bp.route('/')
@user_require(False)
def get_all_pods():
    return get_core(g.zone).list_pods()


@bp.route('/<name>')
@user_require(False)
def get_pod(name):
    return _get_pod(name)


@bp.route('/<name>/nodes')
@user_require(False)
def get_pod_nodes(name):
    pod = _get_pod(name)
    return get_core(g.zone).get_pod_nodes(pod.name)


@bp.route('/<name>/containers')
@user_require(False)
def get_pod_containers(name):
    pod = _get_pod(name)
    return Container.get_by(zone=g.zone, podname=pod.name)


@bp.route('/<name>/networks')
@user_require(False)
def list_networks(name):
    pod = _get_pod(name)
    return get_core(g.zone).list_networks(pod.name)
