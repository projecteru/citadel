# -*- coding: utf-8 -*-
from flask import abort, request
from marshmallow import ValidationError

from citadel.libs.datastructure import AbortDict
from citadel.libs.view import create_api_blueprint, DEFAULT_RETURN_VALUE
from citadel.models.app import App, Release
from citadel.models.base import ModelCreateError
from citadel.models.container import Container
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
    return app.get_env_sets()


@bp.route('/<name>/env/<envname>', methods=['GET', 'PUT', 'POST', 'DELETE'])
def app_env_action(name, envname):
    app = _get_app(name)
    if request.method == 'GET':
        env = app.get_env_set(envname)
        if not env:
            abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

        return DEFAULT_RETURN_VALUE
    elif request.method in ('PUT', 'POST'):
        data = request.get_json()
        app.add_env_set(envname, data)
        return DEFAULT_RETURN_VALUE
    elif request.method == 'DELETE':
        deleted = app.remove_env_set(envname)
        if not deleted:
            abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

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
    branch = data.get('branch')

    group = get_project_group(git)
    all_groups = get_gitlab_groups()
    if not group or group not in all_groups:
        abort(400, 'Only project under a group can be registered, your git repo is %s' % git)

    app = App.get_or_create(name, git)
    if not app:
        abort(400, 'Error during create an app (%s, %s, %s)' % (name, git, sha))

    if not app.gitlab_project.as_dict().get('description'):
        abort(400, 'Must write gitlab project description, we want to know what this app does, and how important it is')

    try:
        release = Release.create(app, sha, branch=branch)
    except (ModelCreateError, ValidationError) as e:
        abort(400, str(e))

    if not release:
        abort(400, 'Error during create a release (%s, %s, %s)' % (name, git, sha))

    if release.raw:
        release.update_image(release.specs.base)

    return release
