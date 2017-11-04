# -*- coding: utf-8 -*-
from flask import g, jsonify, Response, request
from itertools import chain

from citadel.libs.datastructure import AbortDict
from citadel.libs.view import create_api_blueprint
from citadel.models.app import Release
from citadel.tasks import ActionError, create_container, remove_container, upgrade_container_dispatch, celery_task_stream_response, celery_task_stream_traceback, build_image
from citadel.views.helper import make_deploy_options


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

    async_result = build_image.delay(repo, sha, uid, artifact)
    task_id = async_result.task_id
    messages = chain(celery_task_stream_response(task_id), celery_task_stream_traceback(task_id))
    return Response(messages, mimetype='application/json')


@bp.route('/deploy', methods=['POST'])
def deploy():
    payload = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    appname = payload['appname']
    repo = payload['repo']
    sha = payload['sha']
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        raise ActionError(400, 'repo %s, %s does not have the right appname in app.yaml' % (repo, sha))

    combo_name = payload.get('combo')
    specs = release.specs
    envname = specs.combos[combo_name].envname if combo_name else payload.get('envname', '')
    deploy_options = make_deploy_options(
        release,
        combo_name=combo_name,
        podname=payload.get('podname'),
        nodename=payload.get('nodename'),
        entrypoint=payload.get('entrypoint'),
        cpu_quota=payload.get('cpu_quota'),
        count=payload.get('count'),
        memory=payload.get('memory'),
        networks=payload.get('networks'),
        envname=envname,
        extra_env=payload.get('extra_env'),
        debug=payload.get('debug'),
        extra_args=payload.get('extra_args'),
    )
    async_result = create_container.delay(deploy_options, sha=payload['sha'], user_id=g.user.id, envname=envname)
    return Response(celery_task_stream_response(async_result.task_id), mimetype='application/json')


@bp.route('/remove', methods=['POST'])
def remove():
    data = AbortDict(request.get_json())
    ids = data['ids']
    async_result = remove_container.delay(ids, user_id=g.user.id)
    return Response(celery_task_stream_response(async_result.task_id), mimetype='application/json')


@bp.route('/upgrade', methods=['POST'])
def upgrade():
    data = AbortDict(request.get_json())
    ids = data['ids']
    repo = data['repo']
    sha = data['sha']

    async_result = upgrade_container_dispatch.delay(ids, repo, sha, user_id=g.user.id)
    return Response(celery_task_stream_response(async_result.task_id), mimetype='application/json')


@bp.errorhandler(ActionError)
def error_handler(e):
    return jsonify({'error': str(e)}), e.code
