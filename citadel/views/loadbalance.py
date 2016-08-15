# coding: utf-8

from flask import g, request, abort, redirect, url_for
from flask_mako import render_template

from citadel.ext import core
from citadel.config import ELB_APP_NAME
from citadel.libs.view import create_page_blueprint

from citadel.models.oplog import OPLog, OPType
from citadel.models.app import App, Release
from citadel.models.loadbalance import ELBInstance, Route
from citadel.views.helper import get_nodes_for_first_pod


bp = create_page_blueprint('loadbalance', __name__, url_prefix='/loadbalance')


@bp.route('/')
def index():
    elb_dict = {}
    for elb in ELBInstance.get_all(g.start, g.limit):
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
    elbs = ELBInstance.get_by_name(name)
    if not elbs:
        return redirect(url_for('loadbalance.index'))

    # 不是admin就别乱改了
    if request.method == 'POST' and g.user.privilege:
        domain = request.form['domain']
        appname = request.form['appname']
        podname = request.form['podname']
        entrypoint = request.form['entrypoint']

        if appname == ELB_APP_NAME:
            abort(400, 'Can not add ELB route for ELB')

        route = Route.create(podname, appname, entrypoint, domain, name)
        if not route:
            abort(400, 'Create route error')

        # 记录oplog
        op_content = {'route_id': route.id}
        op_content.update(route.to_dict())
        OPLog.create(g.user.id, OPType.CREATE_ELB_ROUTE, content=op_content)

    routes = Route.get_by_elb(name)

    all_apps = [a for a in App.get_all(limit=100) if a and a.name != ELB_APP_NAME]
    return render_template('/loadbalance/elb.mako', name=name, elbs=elbs,
                           routes=routes, all_apps=all_apps)
