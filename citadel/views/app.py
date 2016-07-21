# -*- coding: utf-8 -*-

import os
from flask import g, request, url_for, redirect
from flask_mako import render_template

from citadel.ext import core
from citadel.config import GITLAB_URL
from citadel.libs.view import create_page_blueprint
from citadel.views.helper import bp_get_app, bp_get_release, get_nodes_for_first_pod
from citadel.network.plugin import get_all_pools

from citadel.models.app import App, Release
from citadel.models.env import Environment
from citadel.models.container import Container
from citadel.models.gitlab import get_file_content


bp = create_page_blueprint('app', __name__, url_prefix='/app')


@bp.route('/')
def index():
    apps = App.get_by_user(g.user.id, g.start, g.limit)
    return render_template('/app/list.mako', apps=apps)


@bp.route('/<name>')
def get_app(name):
    app = bp_get_app(name, g.user)
    releases = Release.get_by_app(app.name, g.start, g.limit)
    containers = Container.get_by_app(app.name, g.start, g.limit)
    return render_template('/app/app.mako', app=app, releases=releases, containers=containers)


@bp.route('/<name>/version/<sha>')
def get_release(name, sha):
    app = bp_get_app(name, g.user)
    release = Release.get_by_app_and_sha(app.name, sha)
    containers = Container.get_by_release(app.name, sha, g.start, g.limit)

    appspecs = get_file_content(app.project_name, 'app.yaml', release.sha)

    envs = Environment.get_by_app(app.name)
    networks = {n['name']: n['ipamV4Config'][0]['PreferredPool'] for n in get_all_pools()}

    pods = core.list_pods()
    nodes = get_nodes_for_first_pod(pods)
    return render_template('/app/release.mako', app=app, release=release, envs=envs,
            appspecs=appspecs, containers=containers, networks=networks, nodes=nodes, pods=pods)


@bp.route('/<name>/env', methods=['GET', 'POST'])
def app_env(name):
    app = bp_get_app(name, g.user)

    if request.method == 'GET':
        envs = Environment.get_by_app(app.name)
        return render_template('/app/env.mako', app=app, envs=envs)

    keys = [key for key in request.form.keys() if key.startswith('key_')]
    env_keys = [request.form[key] for key in keys]
    env_dict = {key: request.form['value_%s' % key] for key in env_keys}

    envname = request.form['env']
    Environment.create(app.name, envname, **env_dict)
    return redirect(url_for('app.app_env', name=name))


@bp.route('/<name>/version/<sha>/gitlab')
def gitlab_url(name, sha):
    app = bp_get_app(name, g.user)
    release = bp_get_release(name, sha)
    url = os.path.join(GITLAB_URL, app.project_name, 'commit', release.sha)
    return redirect(url)
