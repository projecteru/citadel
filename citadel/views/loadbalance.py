# coding: utf-8

from flask import g, request, abort
from flask_mako import render_template

from citadel.ext import core
from citadel.config import ELB_SHA, ELB_APP_NAME
from citadel.libs.view import create_page_blueprint
from citadel.views.helper import get_nodes_for_first_pot

from citadel.models.app import App, Release
from citadel.models.balancer import LoadBalancer


bp = create_page_blueprint('loadbalance', __name__, url_prefix='/loadbalance')


@bp.route('/')
def index():
    elbs = LoadBalancer.get_all(g.start, g.limit)
    pods = core.list_pods()

    app = App.get_by_name(ELB_APP_NAME)
    if not app:
        abort(400, 'Bad ELB_APP_NAME: %s', ELB_APP_NAME)

    nodes = get_nodes_for_first_pot(pods)
    releases = Release.get_by_app(app.name, limit=20)
    return render_template('/loadbalance/list.mako', elbs=elbs, pods=pods, releases=releases, nodes=nodes)


@bp.route('/<id>', methods=['POST', 'GET'])
def get_elb(id):
    elb = LoadBalancer.get(id)
    if not elb:
        abort(404)

    if request.method == 'POST':
        ip = request.form['ip']
        domain = request.form['domain']
        if ip and domain:
            elb.add_special_record(ip, domain)
        else:
            appname = request.form['appname']
            podname = request.form['podname']
            entrypoint = request.form['entrypoint']
            elb.add_record(podname, appname, entrypoint, domain)

    records = elb.get_records()
    srecords = elb.get_special_records()
    analysis_dict = elb.get_all_analysis()

    all_apps = [a for a in App.get_all(limit=100) if a]
    return render_template('/loadbalance/elb.mako',
                           elb=elb, records=records, srecords=srecords,
                           analysis_dict=analysis_dict,
                           all_apps=all_apps)
