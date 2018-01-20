# -*- coding: utf-8 -*-
from flask import abort, request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from webargs.flaskparser import use_args

from citadel.libs.validation import ComboSchema, RegisterSchema
from citadel.libs.view import create_api_blueprint, DEFAULT_RETURN_VALUE
from citadel.models.app import App, Release, Combo
from citadel.models.container import Container


bp = create_api_blueprint('app', __name__, 'app')


def _get_app(appname):
    app = App.get_by_name(appname)
    if not app:
        abort(404, 'App not found: {}'.format(appname))
    return app


def _get_release(appname, sha):
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(404, 'Release `%s, %s` not found' % (appname, sha))

    return release


@bp.route('/<appname>')
def get_app(appname):
    return _get_app(appname)


@bp.route('/<appname>/containers')
def get_app_containers(appname):
    app = _get_app(appname)
    return Container.get_by(appname=app.name)


@bp.route('/<appname>/releases')
def get_app_releases(appname):
    app = _get_app(appname)
    return Release.get_by_app(app.name)


@bp.route('/<appname>/env')
def get_app_envs(appname):
    app = _get_app(appname)
    return app.get_env_sets()


@bp.route('/<appname>/env/<envname>', methods=['PUT'])
def create_app_env(appname, envname):
    app = _get_app(appname)
    data = request.get_json()
    try:
        app.add_env_set(envname, data)
    except ValueError as e:
        abort(400, str(e))

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/env/<envname>', methods=['POST'])
def update_app_env(appname, envname):
    app = _get_app(appname)
    data = request.get_json()
    try:
        app.update_env_set(envname, data)
    except ValueError as e:
        abort(400, str(e))

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/env/<envname>')
def get_app_env(appname, envname):
    app = _get_app(appname)
    env = app.get_env_set(envname)
    if not env:
        abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

    return env


@bp.route('/<appname>/env/<envname>', methods=['DELETE'])
def delete_app_env(appname, envname):
    app = _get_app(appname)
    deleted = app.remove_env_set(envname)
    if not deleted:
        abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/combo')
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


@bp.route('/<appname>/version/<sha>')
def get_release(appname, sha):
    return _get_release(appname, sha)


@bp.route('/<appname>/version/<sha>/containers')
def get_release_containers(appname, sha):
    release = _get_release(appname, sha)
    return Container.get_by(appname=appname, sha=release.sha)


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
