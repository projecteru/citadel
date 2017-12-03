# -*- coding: utf-8 -*-
from flask import g, abort, session, request, Blueprint, jsonify
from humanfriendly import parse_size

from citadel.config import ELB_APP_NAME, ELB_POD_NAME, DEFAULT_ZONE
from citadel.libs.jsonutils import jsonize
from citadel.libs.utils import logger
from citadel.libs.view import DEFAULT_RETURN_VALUE, ERROR_CODES
from citadel.models import Container
from citadel.models.app import AppUserRelation, Release
from citadel.models.loadbalance import ELBRule, update_elb_for_containers, UpdateELBAction
from citadel.models.oplog import OPType, OPLog
from citadel.rpc.client import get_core
from citadel.tasks import ActionError, create_elb_instance_upon_containers, create_container, remove_container
from citadel.views.helper import bp_get_app, bp_get_balancer


bp = Blueprint('ajax', __name__, url_prefix='/ajax')


def _error_hanlder(error):
    return jsonify({'error': error.description}), error.code


for code in ERROR_CODES:
    bp.errorhandler(code)(_error_hanlder)


@bp.route('/app/<name>/delete-env', methods=['POST'])
@jsonize
def delete_app_env(name):
    envname = request.form['env']
    app = bp_get_app(name)
    OPLog.create(g.user.id, OPType.DELETE_ENV, app.name, content={'envname': envname})
    deleted = app.remove_env_set(envname)
    if not deleted:
        abort(404, 'App `%s` has no env `%s`' % (app.name, envname))

    return DEFAULT_RETURN_VALUE


@bp.route('/release/<release_id>/entrypoints')
@jsonize
def get_release_entrypoints(release_id):
    release = Release.get(release_id)
    if not release:
        abort(404, 'Release %s not found' % release_id)

    if not (release.specs and release.specs.entrypoints):
        abort(404, 'Release %s has no entrypoints')

    return list(release.specs.entrypoints.keys())


@bp.route('/debug-container', methods=['POST'])
@jsonize
def debug_container():
    payload = request.get_json()
    container_ids = payload['container_id']
    if isinstance(container_ids, str):
        container_ids = [container_ids]

    containers = [Container.get_by_container_id(i) for i in container_ids]
    for c in containers:
        c.mark_debug()

    update_elb_for_containers(containers, UpdateELBAction.REMOVE)
    return DEFAULT_RETURN_VALUE


@bp.route('/pods')
@jsonize
def get_all_pods():
    return get_core(g.zone).list_pods()


@bp.route('/pod/<name>/nodes')
@jsonize
def get_pod_nodes(name):
    return get_core(g.zone).get_pod_nodes(name)


@bp.route('/loadbalance', methods=['POST'])
@jsonize
def create_loadbalance():
    # TODO: validation
    logger.debug('Got create_loadbalance payload: %s', request.data)
    payload = request.get_json()
    release = Release.get(payload['releaseid'])
    envname = payload['envname']
    env_set = release.app.get_env_set(envname)
    env_vars = env_set.to_env_vars()
    name = env_set.get('ELBNAME', 'unnamed')
    user_id = g.user.id
    sha = release.sha

    deploy_options = {
        'specs': release.specs_text,
        'appname': ELB_APP_NAME,
        'image': release.image,
        'podname': ELB_POD_NAME,
        'nodename': payload.get('nodename', ''),
        'entrypoint': payload['entrypoint'],
        'cpu_quota': float(payload.get('cpu', 2)),
        'count': 1,
        'memory': parse_size('2GiB', binary=True),
        'networks': {},
        'env': env_vars,
        'zone': g.zone,
    }
    try:
        grpc_message = create_container(deploy_options=deploy_options,
                                        sha=sha,
                                        envname=envname,
                                        user_id=user_id)[0]
        container_id = grpc_message['id']
        create_elb_instance_upon_containers(container_id, name, sha,
                                            comment=payload['comment'],
                                            user_id=user_id)
    except ActionError as e:
        return {'error': str(e)}, 500
    return DEFAULT_RETURN_VALUE


@bp.route('/loadbalance/<id>/remove', methods=['POST'])
@jsonize
def remove_loadbalance(id):
    elb = bp_get_balancer(id)
    if elb.is_only_instance():
        elb.clear_rules()

    try:
        remove_container(elb.container_id, user_id=g.user.id)
        elb.delete()
    except ActionError as e:
        return {'error': str(e)}, 500
    return DEFAULT_RETURN_VALUE


@bp.route('/<name>/delete', methods=['POST'])
@jsonize
def delete_rule(name):
    payload = request.get_json()
    domain = payload['domain']
    rules = ELBRule.get_by(zone=g.zone, elbname=name, domain=domain)
    if not rules:
        return {'error': 'Rule not found'}, 404

    if len(rules) > 1:
        return {'error': '这数据有问题，你快找平台看看'}, 500

    rule = rules[0]
    if not AppUserRelation.user_permitted_to_app(g.user.id, name):
        return {'error': 'You can\'t do this'}, 400

    if not rule.delete():
        return {'error': 'Error during delete rule'}, 500

    return DEFAULT_RETURN_VALUE


@bp.route('/switch-zone', methods=['POST'])
@jsonize
def switch_zone():
    zone = request.values.get('zone', DEFAULT_ZONE)
    session['zone'] = zone
    return DEFAULT_RETURN_VALUE


@bp.before_request
def access_control():
    # loadbalance和admin的不是admin就不要乱搞了
    if not g.user.privilege and (request.path.startswith('/ajax/admin') or request.path.startswith('/ajax/loadbalance')):
        abort(403, 'Only for admin')
