# coding: utf-8
from flask import g, request, url_for, redirect, abort
from flask_mako import render_template

from citadel import flask_app
from citadel.libs.view import create_page_blueprint
from citadel.models.app import AppUserRelation, App
from citadel.models.container import Container
from citadel.models.oplog import OPLog
from citadel.models.user import get_users, get_user
from citadel.rpc import core


bp = create_page_blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
def index():
    return redirect(url_for('admin.pods'))


@bp.route('/pod')
def pods():
    pods = core.list_pods()
    return render_template('/admin/pods.mako', pods=pods)


@bp.route('/pod/<name>/nodes')
def get_pod_nodes(name):
    pod = core.get_pod(name)
    if not pod:
        abort(404)

    nodes = core.get_pod_nodes(name)
    return render_template('/admin/pod_nodes.mako', pod=pod, nodes=nodes)


@bp.route('/pod/<podname>/node/<nodename>/containers')
def get_node_containers(podname, nodename):
    pod = core.get_pod(podname)
    if not pod:
        abort(404)
    node = core.get_node(podname, nodename)
    if not node:
        abort(404)

    containers = Container.get_by_node(nodename, g.start, g.limit)
    return render_template('/admin/node_containers.mako',
                           pod=pod,
                           node=node,
                           containers=containers)


@bp.route('/user')
def users():
    users = get_users(g.start, g.limit, q=request.args.get('q'))
    return render_template('/admin/users.mako', users=users)


@bp.route('/user/<identifier>', methods=['GET', 'POST'])
def user_info(identifier):
    user = get_user(identifier)
    if not user:
        abort(404)

    if request.method == 'POST':
        appname = request.form['name']
        AppUserRelation.add(appname, user.id)

    apps = App.get_by_user(user.id, limit=100)
    all_apps = App.get_all(limit=100)
    all_apps = [app for app in all_apps if app not in apps]
    return render_template('/admin/user_info.mako',
                           user=user,
                           apps=apps,
                           all_apps=all_apps)


@bp.route('/oplog')
def oplog():
    oplogs = OPLog.get_all(g.start, g.limit)
    return render_template('/admin/oplog.mako', oplogs=oplogs)


@bp.before_request
def access_control():
    if not g.user.privilege:
        abort(403, 'Only for admin')


flask_app.register_blueprint(bp)
