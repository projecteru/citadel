# coding: utf-8

from flask import abort, g, request

from citadel.libs.view import create_api_blueprint
from citadel.libs.datastructure import AbortDict
from citadel.models.app import App, Release
from citadel.models.container import Container


bp = create_api_blueprint('app', __name__, 'app')


@bp.route('/<name>', methods=['GET'])
def get_app(name):
    app = App.get_by_name(name)
    if not app:
        abort(404, 'app `%s` not found' % name)
    return app


@bp.route('/<name>/containers', methods=['GET'])
def get_app_containers(name):
    app = App.get_by_name(name)
    if not app:
        abort(404, 'app `%s` not found' % name)
    return Container.get_by_app(app.name, g.start, g.limit)


@bp.route('/<name>/releases', methods=['GET'])
def get_app_releases(name):
    app = App.get_by_name(name)
    if not app:
        abort(404, 'app `%s` not found' % name)
    return Release.get_by_app(name)


@bp.route('/<name>/version/<sha>', methods=['GET'])
def get_release(name, sha):
    release = Release.get_by_app_and_sha(name, sha)
    if not release:
        abort(404, 'release `%s, %s` not found' % (name, sha))
    return release


@bp.route('/<name>/version/<sha>/containers', methods=['GET'])
def get_release_containers(name, sha):
    release = Release.get_by_app_and_sha(name, sha)
    if not release:
        abort(404, 'release `%s, %s` not found' % (name, sha))
    return Container.get_by_release(name, sha, g.start, g.limit)


@bp.route('/register', methods=['POST'])
def register_release():
    data = AbortDict(request.get_json())

    name = data['name']
    git = data['git']
    sha = data['sha']

    app = App.get_or_create(name, git)
    if not app:
        abort(400, 'error during create an app (%s, %s, %s)' % (name, git, sha))

    release = Release.create(app, sha)
    if not release:
        abort(400, 'error during create a release (%s, %s, %s)' % (name, git, sha))
    return release
