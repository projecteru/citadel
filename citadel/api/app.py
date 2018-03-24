# -*- coding: utf-8 -*-

from flask import abort, request, g
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from webargs.flaskparser import use_args

from citadel.libs.validation import ComboSchema, RegisterSchema, SimpleNameSchema, UserSchema
from citadel.libs.view import create_api_blueprint, DEFAULT_RETURN_VALUE, user_require
from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.user import User


bp = create_api_blueprint('app', __name__, 'app')


def _get_app(appname):
    app = App.get_by_name(appname)
    if not app:
        abort(404, 'App not found: {}'.format(appname))

    if not g.user.granted_to_app(app):
        abort(403, 'You\'re not granted to this app, ask administrators for permission')

    return app


def _get_release(appname, sha):
    release = Release.get_by_app_and_sha(appname, sha)
    if not release:
        abort(404, 'Release `%s, %s` not found' % (appname, sha))

    if not g.user.granted_to_app(release.app):
        abort(403, 'You\'re not granted to this app, ask administrators for permission')

    return release


@bp.route('/')
@user_require(False)
def list_app():
    """List all the apps associated with the current logged in user, for
    administrators, list all apps

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "id": 10001,
                "created": "2018-03-21 14:54:06",
                "updated": "2018-03-21 14:54:07",
                "name": "test-app",
                "git": "git@github.com:projecteru2/citadel.git",
                "tackle_rule": {},
                "env_sets": {"prodenv": {"foo": "some-env-content"}}
            }
        ]
    """
    return g.user.list_app()


@bp.route('/<appname>')
@user_require(False)
def get_app(appname):
    """Get a single app

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "id": 10001,
            "created": "2018-03-21 14:54:06",
            "updated": "2018-03-21 14:54:07",
            "name": "test-app",
            "git": "git@github.com:projecteru2/citadel.git",
            "tackle_rule": {},
            "env_sets": {"prodenv": {"foo": "some-env-content"}}
        }
    """
    return _get_app(appname)


@bp.route('/<appname>/users')
@user_require(False)
def get_app_users(appname):
    """List users who has permissions to the specified app

    .. todo::

        * write tests for this API
        * add example response
    """
    app = _get_app(appname)
    return app.list_users()


@bp.route('/<appname>/users', methods=['PUT'])
@use_args(UserSchema())
@user_require(False)
def grant_user(args, appname):
    """Grant permission to a user

    :<json string username: you know what this is
    :<json int user_id: must provide either username or user_id
    """
    app = _get_app(appname)
    if args['username']:
        user = User.get_by_name(args['username'])
    else:
        user = User.get(args['user_id'])

    try:
        app.grant_user(user)
    except IntegrityError as e:
        pass

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/users', methods=['DELETE'])
@use_args(UserSchema())
@user_require(False)
def revoke_user(args, appname):
    """Revoke someone's permission to a app

    :<json string username: you know what this is
    :<json int user_id: must provide either username or user_id
    """
    app = _get_app(appname)
    if args['username']:
        user = User.get_by_name(args['username'])
    else:
        user = User.get(args['user_id'])

    return app.revoke_user(user)


@bp.route('/<appname>/containers')
@user_require(False)
def get_app_containers(appname):
    """Get all containers of the specified app

    .. todo::

        * add example response
        * test this API
    """
    app = _get_app(appname)
    return Container.get_by(appname=app.name)


@bp.route('/<appname>/releases')
@user_require(False)
def get_app_releases(appname):
    """List every release of the specified app

    .. todo::

        * add example response
        * test this API
    """
    app = _get_app(appname)
    return Release.get_by_app(app.name)


@bp.route('/<appname>/env')
@user_require(False)
def get_app_envs(appname):
    """List all env sets for the specified app

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "prodenv": {
                "password": "secret"
            },
            "testenv": {
                "password": "not-so-secret"
            }
        }
    """
    app = _get_app(appname)
    return app.get_env_sets()


@bp.route('/<appname>/env/<envname>', methods=['PUT'])
@user_require(False)
def create_app_env(appname, envname):
    """Create a environmental variable set

    ..  http:example:: curl wget httpie python-requests

        GET /<appname>/env/<envname> HTTP/1.1
        Accept: application/json

        {
            "HTTP_PROXY": "whatever",
            "HTTPS_PROXY": "whatever"
        }
    """
    app = _get_app(appname)
    data = request.get_json()
    try:
        app.add_env_set(envname, data)
    except ValueError as e:
        abort(400, str(e))

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/env/<envname>', methods=['POST'])
@user_require(False)
def update_app_env(appname, envname):
    """Edit the specified env set, usage is the same as :http:get:`/api/app/(appname)/env/(envname)`"""
    app = _get_app(appname)
    data = request.get_json()
    try:
        app.update_env_set(envname, data)
    except ValueError as e:
        abort(400, str(e))

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/env/<envname>')
@user_require(False)
def get_app_env(appname, envname):
    """Get the content of the specified environmental variable set

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "bar": "whatever",
            "FOO": "\\"",
            "foo": "\'"
        }
    """
    app = _get_app(appname)
    env = app.get_env_set(envname)
    if not env:
        abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

    return env


@bp.route('/<appname>/env/<envname>', methods=['DELETE'])
@user_require(False)
def delete_app_env(appname, envname):
    """Delete the specified environmental variable set"""
    app = _get_app(appname)
    deleted = app.remove_env_set(envname)
    if not deleted:
        abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/combo')
@user_require(False)
def get_app_combos(appname):
    """Get all the combos for the specified app

    .. todo::

        * write tests for this API
        * add example response
    """
    app = _get_app(appname)
    return app.get_combos()


@bp.route('/<appname>/combo', methods=['PUT'])
@use_args(ComboSchema())
@user_require(False)
def create_combo(args, appname):
    """Create a combo for the specified app

    :<json string name: required, the combo name
    :<json string entrypoint_name: required
    :<json string podname: required
    :<json string nodename: optional, provide this only when your app can only be deployed in one machine
    :<json string extra_args: optional, extra arguments to the entrypoint command, e.g. :code:`[python -m http.server] --bind 0.0.0.0`
    :<json list networks: required, list of network names, which can be obtained using :http:get:`/api/pod/(name)/networks`
    :<json float cpu_quota: required
    :<json memory: required, can provide int (in bytes) or string values, like :code:`"128MB"` or :code:`134217728`, when the provided value is string, it'll be parsed by :py:func:`humanfriendly.parse_size(binary=True) <humanfriendly.parse_size>`
    :<json string count: number of containers, default to 1
    :<json string envname: optional, name of the environment variable set to use
    """
    app = _get_app(appname)
    try:
        return app.create_combo(**args)
    except IntegrityError as e:
        abort(400, str(e))


@bp.route('/<appname>/combo', methods=['POST'])
@use_args(ComboSchema())
@user_require(False)
def update_combo(args, appname):
    """Edit the combo value for the specified app

    :<json string name: required, the combo name
    :<json string entrypoint_name: required
    :<json string podname: required
    :<json string nodename: optional, provide this only when your app can only be deployed in one machine
    :<json string extra_args: optional, extra arguments to the entrypoint command, e.g. :code:`[python -m http.server] --bind 0.0.0.0`
    :<json list networks: required, list of network names, which can be obtained using :http:get:`/api/pod/(name)/networks`
    :<json float cpu_quota: required
    :<json memory: required, can provide int (in bytes) or string values, like :code:`"128MB"` or :code:`134217728`, when the provided value is string, it'll be parsed by :py:func:`humanfriendly.parse_size(binary=True) <humanfriendly.parse_size>`
    :<json string count: number of containers, default to 1
    :<json string envname: optional, name of the environment variable set to use
    """
    app = _get_app(appname)
    combo_name = args.pop('name')
    combo = app.get_combo(combo_name)
    if not combo:
        abort(404, 'Combo {} not found'.format(combo_name))

    return combo.update(**args)


@bp.route('/<appname>/combo', methods=['DELETE'])
@use_args(SimpleNameSchema())
@user_require(False)
def delete_combo(args, appname):
    """Delete one combo for the specified app

    :<json string name: the combo name
    """
    app = _get_app(appname)
    app.delete_combo(args['name'])
    return DEFAULT_RETURN_VALUE


@bp.route('/<appname>/version/<sha>')
@user_require(False)
def get_release(appname, sha):
    """Get one release of the specified app

    .. todo::

        * add example response
        * test this API
    """
    return _get_release(appname, sha)


@bp.route('/<appname>/version/<sha>/containers')
@user_require(False)
def get_release_containers(appname, sha):
    """Get all containers of the specified release

    .. todo::

        * add example response
        * test this API
    """
    release = _get_release(appname, sha)
    return Container.get_by(appname=appname, sha=release.sha)


@bp.route('/register', methods=['POST'])
@use_args(RegisterSchema())
@user_require(False)
def register_release(args):
    """Register a release of the specified app

    :<json string appname: required
    :<json string sha: required, must be length 40
    :<json string git: required, the repo address using git protocol, e.g. :code:`git@github.com:projecteru2/citadel.git`
    :<json string specs_text: required, the yaml specs for this app
    :<json string branch: optional git branch
    :<json string git_tag: optional git tag
    :<json string commit_message: optional commit message
    :<json string author: optional author
    """
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
