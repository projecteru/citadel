# coding: utf-8
from flask import abort, g

from citadel.rpc import core
from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container


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
