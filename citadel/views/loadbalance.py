# coding: utf-8
from flask import g, request, abort
from flask_mako import render_template

from citadel.config import ELB_APP_NAME
from citadel.ext import core
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release
from citadel.models.balancer import LoadBalancer, Route
from citadel.views.helper import get_nodes_for_first_pod


bp = create_page_blueprint('loadbalance', __name__, url_prefix='/loadbalance')


@bp.route('/')
def index():
    elb_dict = {}
    for elb in LoadBalancer.get_all(g.start, g.limit):
        elb_dict.setdefault(elb.name, []).append(elb)
    pods = core.list_pods()

    app = App.get_by_name(ELB_APP_NAME)
    if not app:
        abort(400, 'Bad ELB_APP_NAME: %s', ELB_APP_NAME)

    nodes = get_nodes_for_first_pod(pods)
    releases = Release.get_by_app(app.name, limit=20)
    return render_template('/loadbalance/list.mako', elb_dict=elb_dict, pods=pods, releases=releases, nodes=nodes)


@bp.route('/<name>', methods=['POST', 'GET'])
def elb(name):
    elbs = LoadBalancer.get_by_name(name)
    if not elbs:
        abort(404, 'No elb found')

    if request.method == 'POST':
        domain = request.form['domain']
        appname = request.form['appname']
        podname = request.form['podname']
        entrypoint = request.form['entrypoint']
        Route.create(podname, appname, entrypoint, domain, name)

    routes = Route.get_by_elb(name)

    all_apps = [a for a in App.get_all(limit=100) if a]
    return render_template('/loadbalance/elb.mako', name=name, elbs=elbs,
                           routes=routes, all_apps=all_apps)
