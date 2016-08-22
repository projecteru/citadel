# coding: utf-8

import json
from flask import g, request, abort, redirect, url_for, jsonify
from flask_mako import render_template

from citadel.rpc import core
from citadel.config import ELB_APP_NAME
from citadel.libs.view import create_page_blueprint

from citadel.models.oplog import OPLog, OPType
from citadel.models.app import App, Release
from citadel.models.loadbalance import ELBInstance, Route, LBClient, ELBRule
from citadel.views.helper import get_nodes_for_first_pod, bp_get_balancer_by_name, need_admin, update_elb

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

@bp.route('/<name>', methods=['GET'])
def elb(name):
    rules = ELBRule.get_by_elb(name)
    all_apps = [a for a in App.get_all(limit=100) if a and a.name != ELB_APP_NAME]
    return render_template('/loadbalance/balancer.mako', name=name, rules=rules, all_apps=all_apps)


@bp.route('/<name>/update_rule/<domain>', methods=['GET', 'POST'])
@need_admin
def update_rule(name, domain):
    if request.method == 'GET':
        return render_template('/loadbalance/update_rule.mako', name=name, domain=domain)

    rule = request.form['rule']
    if not rule:
        abort(400)

    succeed, msg = update_elb(name, domain, rule)
    if succeed:
        return redirect(url_for('loadbalance.elb', name=name))
    return jsonify(msg)

@bp.route('/<name>/add_rule', methods=['GET', 'POST'])
@need_admin
def add_rule(name):
    if request.method == 'GET':
        return render_template('/loadbalance/add_rule.mako', name=name)

    domain = request.form['domain']
    rule = request.form['rule']

    if not domain or not rule:
        abort(400)

    succeed, msg = update_elb(name, domain, rule)
    if succeed:
        ELBRule.create(name, domain)
        return redirect(url_for('loadbalance.elb', name=name))
    return jsonify(msg)

@bp.route('/<name>/add_general_rule', methods=['POST'])
@need_admin
def add_general_rule(name):
    app = request.form['appname']
    entrypoint = request.form['entrypoint']
    pod = request.form['podname']
    backend = '{}_{}_{}'.format(app, entrypoint, pod)

    domain = request.form['domain']
    if not domain:
        abort(400)

    rule = {
        "default": "rule0",
        "rules_name": ["rule0"],
        "init_rule": "rule0",
        "backends": [backend],
        "rules": {
            "rule0": {"type": "general", "conditions": [{"backend": backend}]}
        }
    }

    succeed, msg = update_elb(name, domain, json.dumps(rule))
    if succeed:
        ELBRule.create(name, domain)
        return redirect(url_for('loadbalance.elb', name=name))
    return jsonify(msg)

@bp.route('/<name>/rule/<domain>', methods=['GET'])
@need_admin
def rule(name, domain):
    elbs = bp_get_balancer_by_name(name)
    elb = elbs[0]
    lb = LBClient(elb.addr)
    rule = lb.get_rule()
    return jsonify({
        'domain': domain,
        'rule': rule['ELB:'+domain]
    })

@bp.route('/<name>/delete_rule/<domain>', methods=['GET'])
@need_admin
def delete_rule(name, domain):
    msg = {}
    succeed = True
    elbs = bp_get_balancer_by_name(name)
    for elb in elbs:
        lb = LBClient(elb.addr)
        if lb.delete_rule(domain):
            msg[elb.addr] = 'ok'
            continue
        msg[elb.addr] = 'failed'
        succeed = False
    if succeed:
        ELBRule.delete(name, domain)
        return redirect(url_for('loadbalance.elb', name=name))
    return jsonify(msg)

def update_elb(name, domain, rule):
    msg = {}
    succeed = True
    elbs = bp_get_balancer_by_name(name)
    rule_content = json.loads(rule)
    for elb in elbs:
        lb = LBClient(elb.addr)
        if not lb.update_rule(domain, rule_content):
            msg[elb.addr] = 'failed'
            succeed = False
    return succeed, msg
