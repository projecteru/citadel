# coding: utf-8
from flask import jsonify, g, request, abort, url_for, redirect
from flask_mako import render_template

from citadel.libs.view import create_page_blueprint
from citadel.models.app import App
from citadel.models.container import Container
from citadel.models.user import get_users, get_user
from citadel.rpc.client import get_core


bp = create_page_blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
def index():
    return redirect(url_for('admin.pods'))


@bp.route('/pod')
def pods():
    pods = get_core(g.zone).list_pods()
    return render_template('/admin/pods.mako', pods=pods)


@bp.route('/pod/<name>/')
def get_pod_nodes(name):
    pod = get_core(g.zone).get_pod(name)
    if not pod:
        abort(404)

    nodes = get_core(g.zone).get_pod_nodes(name)
    return render_template('/admin/pod_nodes.mako', pod=pod, nodes=nodes)


@bp.route('/pod/<podname>/<nodename>', methods=['GET', 'DELETE', 'POST'])
def node(podname, nodename):
    containers = Container.get_by(nodename=nodename, zone=g.zone)
    if request.method == 'DELETE':
        if containers:
            return jsonify({'error': 'Node not empty'}), 400
        get_core(g.zone).remove_node(nodename, podname)
        return jsonify({'message': 'OK'})

    if request.method == 'POST':
        available = (request.get_json() or request.values).get('available', True)
        get_core(g.zone).set_node_availability(podname, nodename, available)
        return jsonify({'message': 'OK'})

    pod = get_core(g.zone).get_pod(podname)
    if not pod:
        abort(404)

    node = get_core(g.zone).get_node(podname, nodename)
    if not node:
        abort(404)

    return render_template('/admin/node_containers.mako',
                           pod=pod,
                           node=node,
                           containers=containers)


@bp.route('/user')
def users():
    users = get_users(g.start, g.limit, q=request.args.get('q'))
    return render_template('/admin/users.mako', users=users)


@bp.route('/user/<identifier>')
def user_info(identifier):
    user = get_user(identifier)
    if not user:
        abort(404)

    apps = App.get_by_user(user.id)
    all_apps = App.get_all(limit=100)
    all_apps = [app for app in all_apps if app not in apps]
    return render_template('/admin/user_info.mako',
                           user=user,
                           apps=apps,
                           all_apps=all_apps)


@bp.before_request
def access_control():
    if not g.user.privilege:
        abort(403, 'Only for admin')
