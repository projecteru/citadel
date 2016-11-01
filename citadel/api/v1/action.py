# coding: utf-8

import json

from flask import jsonify, request, Response

from citadel.action import (build_image, create_container, remove_container,
                            upgrade_container, action_stream, ActionError)
from citadel.libs.agent import EruAgentError, EruAgentClient
from citadel.libs.datastructure import AbortDict
from citadel.libs.view import create_api_blueprint
from citadel.rpc import core


# 把action都挂在/api/:version/下, 不再加前缀
# 也不需要他帮忙自动转JSON了
bp = create_api_blueprint('action', __name__, jsonize=False)


@bp.route('/build', methods=['POST'])
def build():
    """
    可以这么玩玩:
    $ http --stream POST localhost:5000/api/v1/build repo=git@gitlab.ricebook.net:tonic/ci-test.git sha=1d74377e99dcfb3fd892f9eaeab91e1e229179ba uid=4401
    """
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    repo = data['repo']
    sha = data['sha']
    artifact = data.get('artifact', '')
    uid = data.get('uid', '')
    gitlab_build_id = data.get('gitlab_build_id', '')

    q = build_image(repo, sha, uid, artifact, gitlab_build_id)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/deploy', methods=['POST'])
def deploy():
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    repo = data['repo']
    sha = data['sha']
    podname = data['podname']
    entrypoint = data['entrypoint']
    cpu = float(data['cpu_quota'])
    count = int(data['count'])
    networks = data.get('networks', {})
    envname = data.get('env', '')
    extra_env = data.get('extra_env', [])
    extra_args = data.get('extra_args', '')
    nodename = data.get('nodename', '')
    raw = bool(data.get('raw', ''))
    debug = data.get('debug', False)

    q = create_container(repo, sha, podname, nodename, entrypoint, cpu, 0, count, networks, envname, extra_env, raw=raw, extra_args=extra_args, debug=debug)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/remove', methods=['POST'])
def remove():
    data = AbortDict(request.get_json())
    ids = data['ids']

    q = remove_container(ids)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/upgrade', methods=['POST'])
def upgrade():
    data = AbortDict(request.get_json())
    ids = data['ids']
    repo = data['repo']
    sha = data['sha']

    q = upgrade_container(ids, repo, sha)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/log', methods=['POST'])
def get_log():
    data = AbortDict(request.get_json())
    appname = data['appname']
    podname = data['podname']
    nodename = data['nodename']

    node = core.get_node(podname, nodename)
    if not node:
        raise ActionError(400, 'Node %s not found' % nodename)

    # use ActionError instead of EruAgentError to client
    client = EruAgentClient(node.ip)
    try:
        resp = client.log(appname)
    except EruAgentError as e:
        raise ActionError(400, e.message)

    def log_producer():
        for data in resp:
            yield json.dumps(data) + '\n'

    return Response(log_producer(), mimetype='application/json')


@bp.errorhandler(ActionError)
def error_handler(e):
    return jsonify({'error': e.message}), e.code
