# -*- coding: utf-8 -*-
from flask import abort, request, g, jsonify, Response
from itertools import chain
from webargs.flaskparser import use_args

from citadel.libs.datastructure import AbortDict
from citadel.libs.validation import DeploySchema
from citadel.libs.view import create_api_blueprint
from citadel.models.app import Release
from citadel.tasks import (ActionError, create_container, remove_container,
                           upgrade_container_dispatch,
                           celery_task_stream_response,
                           celery_task_stream_traceback, build_image)


# 把action都挂在/api/:version/下, 不再加前缀
# 也不需要他帮忙自动转JSON了
bp = create_api_blueprint('action', __name__, jsonize=False)


@bp.route('/build', methods=['POST'])
def build():
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    appname = data['appname']
    sha = data['sha']
    uid = data.get('uid', '')

    async_result = build_image.delay(appname, sha, uid)
    task_id = async_result.task_id
    messages = chain(celery_task_stream_response(task_id), celery_task_stream_traceback(task_id))
    return Response(messages, mimetype='application/json')


@bp.route('/deploy', methods=['POST'])
@use_args(DeploySchema())
def deploy(args):
    appname = args['appname']
    sha = args['sha']
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(404, 'Release {} for {} not found'.format(sha, appname))

    combo_name = args['combo_name']
    app = release.app
    combo = app.get_combo(combo_name)
    if not combo:
        abort(404, 'Combo {} for {} not found'.format(combo_name, appname))

    async_result = create_container.delay(zone=g.zone, user_id=g.user.id, **args)
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
