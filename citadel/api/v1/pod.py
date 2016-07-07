# coding: utf-8

from flask import abort

from citadel.ext import core
from citadel.libs.view import create_api_blueprint


bp = create_api_blueprint('pod', __name__, 'pod')


@bp.route('/', methods=['GET'])
def get_all_pods():
    return core.list_pods()


@bp.route('/<name>', methods=['GET'])
def get_pod(name):
    pod = core.get_pod(name)
    if not pod:
        abort(404, 'pod `%s` not found' % name)
    return pod


@bp.route('/<name>/nodes', methods=['GET'])
def get_pod_nodes(name):
    pod = core.get_pod(name)
    if not pod:
        abort(404, 'pod `%s` not found' % name)
    return core.get_pod_nodes(name)
