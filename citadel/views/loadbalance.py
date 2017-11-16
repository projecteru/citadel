# -*- coding: utf-8 -*-
from flask import request, abort, redirect, url_for, jsonify, flash, g
from flask_mako import render_template

from citadel.config import ELB_APP_NAME, ELB_POD_NAME
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release
from citadel.libs.exceptions import ModelCreateError
from citadel.models.loadbalance import ELBInstance, ELBRule, get_elb_client
from citadel.rpc import get_core
from citadel.views.helper import need_admin


bp = create_page_blueprint('loadbalance', __name__, url_prefix='/loadbalance')


def _cleanse_domain(url):
    """remove scheme and trailing slash from url"""
    return url.split('://')[-1].strip('/')


@bp.route('/')
def index():
    elb_dict = {}
    current_instances = ELBInstance.get_by(zone=g.zone)
    occupied_pods = set()
    for elb in current_instances:
        if not elb.container:
            elb.delete()
            continue

        occupied_pods.add(elb.container.nodename)
        elb_dict.setdefault(elb.name, []).append(elb)

    app = App.get_by_name(ELB_APP_NAME)
    if not app:
        abort(404, 'ELB app not found: {}'.format(ELB_APP_NAME))

    # elb container is deployed in host network mode, that means one elb
    # instance per node
    nodes = [n for n in get_core(g.zone).get_pod_nodes(ELB_POD_NAME) if n.name not in occupied_pods]
    env_sets = app.get_env_sets()
    releases = Release.get_by_app(ELB_APP_NAME, limit=20)
    return render_template('/loadbalance/list.mako',
                           elb_dict=elb_dict,
                           podname=ELB_POD_NAME,
                           appname=ELB_APP_NAME,
                           releases=releases,
                           nodes=nodes,
                           env_sets=env_sets)


@bp.route('/<name>', methods=['GET'])
def elb(name):
    rules = ELBRule.get_by(elbname=name, zone=g.zone)
    all_apps = [a for a in App.get_all(limit=100) if a and a.name != ELB_APP_NAME]
    if not all_apps:
        abort(404, 'NO APPS AT ALL')

    elbs = ELBInstance.get_by(name=name, zone=g.zone)
    if not elbs and not rules:
        abort(404, 'No instance found for ELB: {}'.format(name))

    return render_template('/loadbalance/balancer.mako',
                           name=name,
                           rules=rules,
                           elbs=elbs,
                           all_apps=all_apps)


@bp.route('/<name>/edit', methods=['GET', 'POST'])
@need_admin
def edit_rule(name):
    domain = request.values['domain']
    if request.method == 'GET':
        return render_template('/loadbalance/edit_rule.mako', name=name, domain=domain)

    rule_content = request.values['rule']
    if not rule_content:
        abort(400)

    rules = ELBRule.get_by(zone=g.zone, elbname=name, domain=domain)
    if not rules:
        abort(404)

    if len(rules) > 1:
        flash('这数据绝逼有问题，你赶紧找平台看看')
        return redirect(url_for('loadbalance.elb', name=name))

    rule = rules[0]
    if not rule.edit_rule(rule_content):
        flash('edit rule failed', 'error')

    return redirect(url_for('loadbalance.elb', name=name))


@bp.route('/<name>/add-rule', methods=['POST'])
@need_admin
def add_rule(name):
    appname = request.form['appname']
    domain = _cleanse_domain(request.form['domain'])
    rule_content = request.form['rule']
    try:
        ELBRule.create(g.zone, appname, name, domain, rule_content)
    except ModelCreateError as e:
        abort(400, str(e))

    return redirect(url_for('loadbalance.elb', name=name))


@bp.route('/<name>/add-general-rule', methods=['POST'])
@need_admin
def add_general_rule(name):
    appname = request.form['appname']
    entrypoint = request.form['entrypoint']
    podname = request.form['podname']

    domain = _cleanse_domain(request.form['domain'])
    if not domain:
        abort(400, 'Bad domain')

    try:
        ELBRule.create(g.zone, name, domain, appname, entrypoint=entrypoint, podname=podname)
    except ModelCreateError as e:
        abort(400, str(e))

    return redirect(url_for('loadbalance.elb', name=name))


@bp.route('/<name>/rule', methods=['GET'])
@need_admin
def rule(name):
    domain = request.args['domain']
    elb = get_elb_client(name, g.zone)
    rule = elb.get_rule(domain)
    return jsonify({
        'domain': domain,
        'rule': rule,
    })
