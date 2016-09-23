# coding: utf-8

from flask import abort, g, request

from citadel.rpc import core
from citadel.libs.view import create_api_blueprint
from citadel.libs.datastructure import AbortDict
from citadel.models.container import Container
from citadel.network.plugin import get_all_networks


bp = create_api_blueprint('pod', __name__, 'pod')


def _get_pod(name):
    pod = core.get_pod(name)
    if not pod:
        abort(404, 'pod `%s` not found' % name)
    return pod


@bp.route('/', methods=['GET'])
def get_all_pods():
    return core.list_pods()


@bp.route('/<name>', methods=['GET'])
def get_pod(name):
    return _get_pod(name)


@bp.route('/<name>/nodes', methods=['GET'])
def get_pod_nodes(name):
    pod = _get_pod(name)
    return core.get_pod_nodes(pod.name)


@bp.route('/<name>/containers', methods=['GET'])
def get_pod_containers(name):
    pod = _get_pod(name)
    return Container.get_by_pod(pod.name, g.start, g.limit)


@bp.route('/<name>/networks', methods=['GET'])
def get_pod_networks(name):
    pod = _get_pod(name)
    return get_all_networks(pod.name)


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
    
    return core.add_node(nodename, endpoint, pod.name, cafile, certfile, keyfile, public)
