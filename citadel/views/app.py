# -*- coding: utf-8 -*-
import os

import tailer
from flask import g, request, abort, flash, jsonify, url_for, redirect
from flask_mako import render_template

from citadel.config import IGNORE_PODS, MFS_LOG_FILE_PATH, GITLAB_URL
from citadel.libs.utils import make_unicode
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release, AppUserRelation
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.gitlab import get_file_content
from citadel.models.oplog import OPLog, OPType
from citadel.models.user import User
from citadel.rpc import core
from citadel.views.helper import bp_get_app, bp_get_release, get_nodes_for_first_pod, get_networks_for_first_pod


bp = create_page_blueprint('app', __name__, url_prefix='/app')


@bp.route('/')
def index():
    apps = App.get_by_user(g.user.id, limit=None)
    return render_template('/app/list.mako', apps=apps)


@bp.route('/<name>')
def get_app(name):
    app = bp_get_app(name)
    releases = Release.get_by_app(app.name, limit=8)
    containers = Container.get_by_app(app.name, limit=None)
    return render_template('/app/app.mako', app=app, releases=releases, containers=containers)


@bp.route('/<name>/version/<sha>', methods=['GET', 'DELETE'])
def release(name, sha):
    app = bp_get_app(name)
    release = Release.get_by_app_and_sha(app.name, sha)
    if not all([app, release]):
        abort(404, 'App or release not found')

    if request.method == 'DELETE':
        if AppUserRelation.user_permitted_to_app(g.user.id, name):
            release.delete()
            return jsonify({'message': 'OK'})
        else:
            flash(u'Don\'t touch me')

    containers = Container.get_by_release(app.name, sha, limit=None)
    appspecs = get_file_content(app.project_name, 'app.yaml', release.sha)
    envs = Environment.get_by_app(app.name)
    # we won't be using pod redis and elb here
    pods = [p for p in core.list_pods() if p.name not in IGNORE_PODS]
    nodes = get_nodes_for_first_pod(pods)
    combos = release.combos
    networks = get_networks_for_first_pod(pods)
    template_name = '/app/release-with-combos.mako' if combos else '/app/release.mako'
    return render_template(template_name, app=app, release=release,
                           envs=envs, appspecs=appspecs, containers=containers,
                           networks=networks, nodes=nodes, pods=pods, combos=combos)


@bp.route('/<name>/env', methods=['GET', 'POST'])
def app_env(name):
    app = bp_get_app(name)

    if request.method == 'GET':
        envs = Environment.get_by_app(app.name)
        return render_template('/app/env.mako', app=app, envs=envs)

    keys = [key for key in request.form.keys() if key.startswith('key_')]
    env_keys = [request.form[key] for key in keys]
    env_dict = {key: request.form['value_%s' % key] for key in env_keys}

    envname = request.form['env']
    Environment.create(app.name, envname, **env_dict)

    # 记录oplog
    op_content = {'envname': envname, 'keys': env_keys}
    OPLog.create(g.user.id, OPType.CREATE_ENV, app.name, content=op_content)

    return redirect(url_for('app.app_env', name=name))


@bp.route('/<name>/permitted-users', methods=['GET', 'POST'])
def app_permitted_users(name):
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        AppUserRelation.delete(name, user_id)

    user_ids = AppUserRelation.get_user_id_by_appname(name)
    users = [User.get(id_) for id_ in user_ids]
    return render_template('/app/permitted-users.mako', users=users)


@bp.route('/<name>/version/<sha>/gitlab')
def gitlab_url(name, sha):
    app = bp_get_app(name)
    release = bp_get_release(name, sha)
    url = os.path.join(GITLAB_URL, app.project_name, 'commit', release.sha)
    return redirect(url)


@bp.route('/<name>/<entrypoint>/log/<date:dt>')
def get_app_log(name, entrypoint, dt):
    bp_get_app(name)
    log_file_path = MFS_LOG_FILE_PATH.format(app_name=name, entrypoint=entrypoint, dt=dt)
    if not os.path.isfile(log_file_path):
        # TODO: redirect to latest log
        abort(404, 'log not found')

    file_length = min([g.limit, 10000])
    log_content = tailer.tail(open(log_file_path), file_length)
    decoded = [make_unicode(l) for l in log_content]
    return render_template('/app/applog.mako', log_content=decoded)
