# -*- coding: utf-8 -*-
from flask import abort, request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from webargs.flaskparser import use_args

from citadel.libs.view import create_api_blueprint, DEFAULT_RETURN_VALUE
from citadel.models.app import App, Release, Combo, ComboSchema, RegisterSchema
from citadel.models.container import Container


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


@bp.route('/<appname>/combo', methods=['GET'])
def get_app_combos(appname):
    app = _get_app(appname)
    return app.get_combos()


@bp.route('/<appname>/combo', methods=['POST'])
@use_args(ComboSchema())
def create_combo(args, appname):
    args.update({'appname': appname})
    try:
        return Combo.create(**args)
    except IntegrityError as e:
        abort(400, str(e))


@bp.route('/<appname>/combo', methods=['DELETE'])
def delete_combo(appname):
    combo_name = request.get_json()['name']
    app = _get_app(appname)
    combo = app.get_combo(combo_name)
    if not combo:
        abort(404)

    combo.delete()
    return DEFAULT_RETURN_VALUE


@bp.route('/<name>/version/<sha>', methods=['GET'])
def get_release(name, sha):
    return _get_release(name, sha)


@bp.route('/<name>/version/<sha>/containers', methods=['GET'])
def get_release_containers(name, sha):
    release = _get_release(name, sha)
    return Container.get_by(appname=name, sha=release.sha)


@bp.route('/register', methods=['POST'])
@use_args(RegisterSchema())
def register_release(args):
    appname = args['appname']
    git = args['git']
    sha = args['sha']
    specs_text = args['specs_text']
    branch = args.get('branch')
    git_tag = args.get('git_tag')
    commit_message = args.get('commit_message')
    author = args.get('author')

    app = App.get_or_create(appname, git)
    if not app:
        abort(400, 'Error during create an app (%s, %s, %s)' % (appname, git, sha))

    try:
        release = Release.create(app, sha, specs_text, branch=branch, git_tag=git_tag,
                                 author=author, commit_message=commit_message)
    except (IntegrityError, ValidationError) as e:
        abort(400, str(e))

    if release.raw:
        release.update_image(release.specs.base)

    return release
