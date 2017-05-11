# -*- coding: utf-8 -*-
from flask import g, request, abort

from citadel.ext import cache
from citadel.libs.datastructure import AbortDict
from citadel.libs.memcap import get_node_memcap, sync_node_memcap
from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container
from citadel.rpc import get_core


bp = create_api_blueprint('pod', __name__, 'pod')


def _get_pod(name):
    pod = get_core(g.zone).get_pod(name)
    if not pod:
        abort(404, 'pod `%s` not found' % name)

    return pod


@bp.route('/', methods=['GET'])
@cache.cached(timeout=60 * 10)
def get_all_pods():
    return get_core(g.zone).list_pods()


@bp.route('/<name>', methods=['GET'])
def get_pod(name):
    return _get_pod(name)


@bp.route('/<name>/nodes', methods=['GET'])
@cache.cached(timeout=60 * 10)
def get_pod_nodes(name):
    pod = _get_pod(name)
    return get_core(g.zone).get_pod_nodes(pod.name)


@bp.route('/<name>/containers', methods=['GET'])
def get_pod_containers(name):
    pod = _get_pod(name)
    return Container.get_by(zone=g.zone, podname=pod.name)


@bp.route('/<name>/networks', methods=['GET'])
@cache.cached(timeout=60 * 10)
def get_pod_networks(name):
    pod = _get_pod(name)
    return get_core(g.zone).get_pod_networks(pod.name)


@bp.route('/<name>/addnode', methods=['PUT', 'POST'])
def add_node(name):
    pod = _get_pod(name)

    json_data = request.get_json()
    data = json_data and AbortDict(json_data) or request.form

    cafile, certfile, keyfile = '', '', ''
    if json_data:
        cafile = data.get('cafile', '')
        certfile = data.get('certfile', '')
        keyfile = data.get('keyfile', '')
    else:
        try:
            cafile = request.files['cafile'].read()
            certfile = request.files['certfile'].read()
            keyfile = request.files['keyfile'].read()
        except KeyError:
            pass

    nodename = data['nodename']
    endpoint = data['endpoint']
    public = bool(data.get('public', ''))

    bundle = (cafile, certfile, keyfile)

    if not all(bundle) and any(bundle):
        abort(400, 'cafile, certfile, keyfile must be either all empty or none empty')

    return get_core(g.zone).add_node(nodename, endpoint, pod.name, cafile, certfile, keyfile, public)


@bp.route('/<name>/getmemcap', methods=['GET'])
def get_memcap(name):
    return get_node_memcap(g.zone, name)


@bp.route('/<name>/syncmemcap', methods=['POST'])
def sync_memcap(name):
    return sync_node_memcap(g.zone, name)
