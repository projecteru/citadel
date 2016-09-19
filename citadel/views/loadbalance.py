# coding: utf-8
from flask import g, request, abort, redirect, url_for, jsonify, flash
from flask_mako import render_template

from citadel.config import ELB_APP_NAME
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release
from citadel.models.loadbalance import ELBInstance, ELBRule
from citadel.rpc import core
from citadel.views.helper import get_nodes_for_first_pod, bp_get_balancer_by_name, need_admin


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
    elbs = ELBInstance.get_by_name(name)
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

    rule = ELBRule.get_by(elbname=name, domain=domain)
    if not rule:
        abort(404)

    if not rule.edit_rule(rule_content):
        flash(u'edit rule failed', 'error')

    return redirect(url_for('loadbalance.elb', name=name))


@bp.route('/<name>/add-rule', methods=['GET', 'POST'])
@need_admin
def add_rule(name):
    if request.method == 'GET':
        all_apps = [a for a in App.get_all(limit=100) if a and a.name != ELB_APP_NAME]
        return render_template('/loadbalance/add_rule.mako', name=name, all_apps=all_apps)

    appname = request.form['appname']
    domain = request.form['domain']
    rule_content = request.form['rule']
    rule = ELBRule.create(appname, name, domain, rule_content)
    if not rule:
        flash(u'create rule failed')

    return redirect(url_for('loadbalance.elb', name=name))


@bp.route('/<name>/add-general-rule', methods=['POST'])
@need_admin
def add_general_rule(name):
    appname = request.form['appname']
    entrypoint = request.form['entrypoint']
    podname = request.form['podname']

    domain = request.form['domain']
    if not domain:
        abort(400)

    r = ELBRule.create(name, domain, appname,
                       rule=None,
                       entrypoint=entrypoint,
                       podname=podname)
    if not r:
        flash(u'create rule failed', 'error')

    return redirect(url_for('loadbalance.elb', name=name))


@bp.route('/<name>/rule', methods=['GET'])
@need_admin
def rule(name):
    domain = request.args['domain']
    elbs = bp_get_balancer_by_name(name)
    elb = elbs[0]
    rule = elb.lb_client.get_rule()
    key = ':'.join([name, domain])
    return jsonify({
        'domain': domain,
        'rule': rule[key]
    })


@bp.route('/<name>/delete', methods=['POST'])
@need_admin
def delete_rule(name):
    domain = request.values['domain']
    rule = ELBRule.get_by(elbname=name, domain=domain)
    if not rule.delete():
        flash(u'error during delete elb', 'error')

    return redirect(url_for('loadbalance.elb', name=name))
