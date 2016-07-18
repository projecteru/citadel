# coding: utf-8
from flask import jsonify, Response
from webargs.flaskparser import use_args

from citadel.action import (build_image, create_container, remove_container,
                            upgrade_container, action_stream, ActionError)
from citadel.libs.datastructure import (repo_field, podname_field,
                                        entrypoint_field, cpu_field,
                                        count_field, sha_field, artifact_field,
                                        uid_field, networks_field,
                                        envname_field, extra_env_field,
                                        ids_field)
from citadel.libs.view import create_api_blueprint


# 把action都挂在/api/:version/下, 不再加前缀
# 也不需要他帮忙自动转JSON了
bp = create_api_blueprint('action', __name__, jsonize=False)


@bp.route('/build', methods=['POST'])
@use_args({
    'repo': repo_field,
    'sha': sha_field,
    'artifact': artifact_field,
    'uid': uid_field,
})
def build(args):
    """
    可以这么玩玩:
    $ http --stream POST localhost:5000/api/v1/build repo=git@gitlab.ricebook.net:tonic/ci-test.git sha=1d74377e99dcfb3fd892f9eaeab91e1e229179ba uid=4401
    """
    q = build_image(args['repo'], args['sha'], args['uid'], args['artifact'])
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/deploy', methods=['POST'])
@use_args({
    'repo': repo_field,
    'sha': sha_field,
    'podname': podname_field,
    'entrypoint': entrypoint_field,
    'cpu': cpu_field,
    'count': count_field,
    'networks': networks_field,
    'envname': envname_field,
    'extra_env': extra_env_field,
})
def deploy(args):
    q = create_container(args['repo'], args['sha'], args['podname'],
                         args['entrypoint'], args['cpu'], args['count'],
                         args['networks'], args['envname'], args['extra_env'])
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/remove', methods=['POST'])
@use_args({'ids': ids_field})
def remove(args):
    q = remove_container(args['ids'])
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/upgrade', methods=['POST'])
@use_args({
    'ids': ids_field,
    'repo': repo_field,
    'sha': sha_field,
})
def upgrade(args):
    q = upgrade_container(args['ids'], args['repo'], args['sha'])
    return Response(action_stream(q), mimetype='application/json')


@bp.errorhandler(ActionError)
def error_handler(e):
    return jsonify({'error': e.message}), e.code
