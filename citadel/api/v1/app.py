# -*- coding: utf-8 -*-
from flask import abort, request

from citadel.libs.datastructure import AbortDict
from citadel.libs.view import create_api_blueprint, DEFAULT_RETURN_VALUE
from citadel.models.app import App, Release
from citadel.models.base import ModelCreateError
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.gitlab import get_project_group, get_gitlab_groups


bp = create_api_blueprint('app', __name__, 'app')


def _get_app(name):
    app = App.get_by_name(name)
    if not app:
        abort(404, 'App not found: {}'.format(name))
    return app


def _get_release(name, sha):
    release = Release.get_by_app_and_sha(name, sha)
    if not release:
        abort(404, 'Release `%s, %s` not found' % (name, sha))

    return release


@bp.route('/<name>', methods=['GET'])
def get_app(name):
    return _get_app(name)


@bp.route('/<name>/containers', methods=['GET'])
def get_app_containers(name):
    app = _get_app(name)
    return Container.get_by(appname=app.name)


@bp.route('/<name>/releases', methods=['GET'])
def get_app_releases(name):
    app = _get_app(name)
    return Release.get_by_app(app.name)


@bp.route('/<name>/env', methods=['GET'])
def get_app_envs(name):
    app = _get_app(name)
    return [e.to_jsonable() for e in Environment.get_by_app(app.name)]


@bp.route('/<name>/env/<envname>', methods=['GET', 'PUT', 'POST', 'DELETE'])
def app_env_action(name, envname):
    app = _get_app(name)
    if request.method == 'GET':
        env = Environment.get_by_app_and_env(app.name, envname)
        if not env:
            abort(404, 'App `%s` has no env `%s`' % (app.name, envname))
        return env.to_jsonable()
    elif request.method in ('PUT', 'POST'):
        data = request.get_json()
        env = Environment.create(app.name, envname, **data)
        return env.to_jsonable()
    elif request.method == 'DELETE':
        env = Environment.get_by_app_and_env(app.name, envname)
        if not env:
            abort(404, 'App `%s` has no env `%s`' % (app.name, envname))
        env.delete()
        return DEFAULT_RETURN_VALUE


@bp.route('/<name>/version/<sha>', methods=['GET'])
def get_release(name, sha):
    return _get_release(name, sha)


@bp.route('/<name>/version/<sha>/containers', methods=['GET'])
def get_release_containers(name, sha):
    release = _get_release(name, sha)
    return Container.get_by(appname=name, sha=release.sha)


@bp.route('/register', methods=['POST'])
def register_release():
    data = AbortDict(request.get_json())
    name = data['name']
    git = data['git']
    sha = data['sha']

    group = get_project_group(git)
    all_groups = get_gitlab_groups()
    if not group or group not in all_groups:
        abort(400, 'Only project under a group can be registered, your git repo is %s' % git)

    app = App.get_or_create(name, git)
    if not app:
        abort(400, 'Error during create an app (%s, %s, %s)' % (name, git, sha))

    try:
        release = Release.create(app, sha)
    except ModelCreateError as e:
        abort(400, str(e))

    if not release:
        abort(400, 'Error during create a release (%s, %s, %s)' % (name, git, sha))

    if release.raw:
        release.update_image(release.specs.base)

    return release
