# -*- coding: utf-8 -*-
import os

from flask import g, request, abort, flash, jsonify, url_for, redirect
from flask_mako import render_template

from citadel.config import IGNORE_PODS, GITLAB_URL, ELB_APP_NAME
from citadel.libs.utils import make_unicode
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release, AppUserRelation
from citadel.models.base import ModelDeleteError
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
    if g.user.privilege and request.values.get('all', type=int):
        apps = [a for a in App.get_all(limit=None) if a.name != ELB_APP_NAME]
    else:
        apps = App.get_by_user(g.user.id, limit=None)

    return render_template('/app/list.mako', apps=apps)


@bp.route('/<name>', methods=['GET', 'DELETE'])
def app(name):
    app = bp_get_app(name)
    if request.method == 'DELETE':
        if not AppUserRelation.user_permitted_to_app(g.user.id, name):
            return jsonify({'message': u'没权限'}), 403
        else:
            try:
                app.delete()
                return jsonify({'message': u'OK'}), 200
            except ModelDeleteError:
                return jsonify({'message': u'容器删干净之后才能删除应用'}), 400

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
        if AppUserRelation.user_permitted_to_app(g.user.id, name) or release.container_list:
            release.delete()
            return jsonify({'message': 'OK'})
        else:
            flash(u'要么没权限，要么还在跑')

    containers = Container.get_by_release(app.name, sha, limit=None)
    appspecs = get_file_content(app.project_name, 'app.yaml', release.sha)
    envs = Environment.get_by_app(app.name)
    # we won't be using pod redis and elb here
    pods = [p for p in core.list_pods() if p.name not in IGNORE_PODS]
    nodes = get_nodes_for_first_pod(pods)
    combos = release.combos
    networks = get_networks_for_first_pod(pods)

    draw_combos = bool(request.values.get('draw_combos', type=int, default=1))
    # if there's combos, nomal users must use them, while admin can switch back
    # to the original deploy UI
    if combos and not draw_combos and g.user.privilege:
        draw_combos = False

    return render_template('/app/release.mako', app=app, release=release,
                           envs=envs, appspecs=make_unicode(appspecs),
                           containers=containers, networks=networks,
                           nodes=nodes, pods=pods, combos=combos,
                           draw_combos=draw_combos)


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
    users = [u for u in users if u]
    return render_template('/app/permitted-users.mako', users=users)


@bp.route('/<name>/version/<sha>/gitlab')
def gitlab_url(name, sha):
    app = bp_get_app(name)
    release = bp_get_release(name, sha)
    url = os.path.join(GITLAB_URL, app.project_name, 'commit', release.sha)
    return redirect(url)
