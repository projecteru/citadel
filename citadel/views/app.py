# -*- coding: utf-8 -*-
import os

from flask import g, request, url_for, redirect
from flask_mako import render_template

from citadel.config import GITLAB_URL
from citadel.rpc import core
from citadel.libs.view import create_page_blueprint

from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.gitlab import get_file_content
from citadel.models.oplog import OPLog, OPType

from citadel.network.plugin import get_all_pools
from citadel.views.helper import bp_get_app, bp_get_release, get_nodes_for_first_pod


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


@bp.route('/<name>/version/<sha>')
def get_release(name, sha):
    app = bp_get_app(name)
    release = Release.get_by_app_and_sha(app.name, sha)
    containers = Container.get_by_release(app.name, sha, limit=None)

    appspecs = get_file_content(app.project_name, 'app.yaml', release.sha)

    envs = Environment.get_by_app(app.name)
    networks = {n['name']: n['ipamV4Config'][0]['PreferredPool'] for n in get_all_pools()}

    pods = core.list_pods()
    nodes = get_nodes_for_first_pod(pods)
    combos = release.get_combos()
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


@bp.route('/<name>/version/<sha>/gitlab')
def gitlab_url(name, sha):
    app = bp_get_app(name)
    release = bp_get_release(name, sha)
    url = os.path.join(GITLAB_URL, app.project_name, 'commit', release.sha)
    return redirect(url)
