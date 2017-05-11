# -*- coding: utf-8 -*-
from itertools import chain

from flask import g, abort, session, request, Blueprint, jsonify, Response
from humanfriendly import parse_size

from citadel.config import ELB_APP_NAME, ELB_POD_NAME, DEFAULT_ZONE
from citadel.libs.jsonutils import jsonize
from citadel.libs.utils import logger
from citadel.libs.view import DEFAULT_RETURN_VALUE, ERROR_CODES
from citadel.models import Container
from citadel.models.app import AppUserRelation, Release
from citadel.models.loadbalance import ELBRule, update_elb_for_containers, UpdateELBAction
from citadel.models.oplog import OPType, OPLog
from citadel.rpc import get_core
from citadel.tasks import ActionError, create_elb_instance_upon_containers, create_container, remove_container, upgrade_container, celery_task_stream_response, celery_task_stream_traceback
from citadel.views.helper import bp_get_app, bp_get_balancer, make_deploy_options


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


@bp.route('/release/<release_id>/deploy', methods=['POST'])
def deploy_release(release_id):
    """部署的ajax接口, oplog在对应action里记录."""
    release = Release.get(release_id)
    if not release:
        abort(404, 'Release %s not found' % release_id)

    if release.name == ELB_APP_NAME:
        abort(400, 'Do not deploy %s through this API' % ELB_APP_NAME)

    specs = release.specs
    if not (specs and specs.entrypoints):
        abort(404, 'Release %s has no entrypoints')

    payload = request.get_json()
    envname = payload.get('envname', '')

    deploy_options = make_deploy_options(
        release,
        podname=payload.get('podname'),
        nodename=payload.get('nodename'),
        entrypoint=payload.get('entrypoint'),
        cpu_quota=payload.get('cpu'),
        count=payload.get('count'),
        memory=payload.get('memory'),
        networks=payload.get('networks'),
        envname=envname,
        extra_env=payload.get('extra_env'),
        debug=payload.get('debug'),
        extra_args=payload.get('extra_args'),
    )
    async_result = create_container.delay(deploy_options=deploy_options,
                                          sha=release.sha,
                                          envname=envname,
                                          user_id=g.user.id)
    task_id = async_result.task_id

    def generate_stream_response():
        """relay grpc message, if in debug mode, stream logs as well"""
        for msg in chain(celery_task_stream_response(task_id), celery_task_stream_traceback(task_id)):
            yield msg

    return Response(generate_stream_response(), mimetype='text/event-stream')


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


@bp.route('/rmcontainer', methods=['POST'])
@jsonize
def remove_containers():
    # 过滤掉ELB的容器, ELB不要走这个方式下线
    payload = request.get_json()
    container_ids = payload['container_id']
    if isinstance(container_ids, str):
        container_ids = [container_ids]

    containers = [Container.get_by_container_id(i) for i in container_ids]
    # mark removing so that users would see some changes, but the actual
    # removing happends in celery tasks
    should_remove = []
    for c in containers:
        if not c:
            continue
        if c.appname == ELB_APP_NAME:
            return {'error': 'Cannot delete ELB container here'}, 400
        c.mark_removing()
        should_remove.append(c.container_id)

    if should_remove:
        remove_container.delay(should_remove, user_id=g.user.id)

    return DEFAULT_RETURN_VALUE


@bp.route('/upgrade-container', methods=['POST'])
def upgrade_containers():
    payload = request.get_json()
    container_ids = payload['container_ids']
    sha = payload['sha']
    containers = [Container.get_by_container_id(cid) for cid in container_ids]
    appnames = set(c.appname for c in containers if c)
    if not appnames:
        abort(400, 'No containers to upgrade')

    if len(appnames) != 1:
        abort(400, 'Cannot upgrade containers across apps')

    container_specs = set(c.release.specs_text for c in containers)
    new_release = containers[0].app.get_release(sha)
    if not new_release:
        abort(400, 'Release {} not found'.format(sha))

    if len(container_specs) != 1 or container_specs.pop() != new_release.specs_text:
        abort(400, 'Cannot upgrade due to app.yaml change')

    if ELB_APP_NAME in appnames:
        abort(400, 'Do not upgrade {} through this API'.format(ELB_APP_NAME))

    async_results = [upgrade_container.delay(cid, sha, user_id=g.user.id) for cid in [c.container_id for c in containers if c]]
    task_ids = [r.task_id for r in async_results]
    messages = chain(celery_task_stream_response(task_ids), celery_task_stream_traceback(task_ids))
    return Response(messages, mimetype='application/json')


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


@bp.route('/admin/revoke-app', methods=['POST'])
@jsonize
def revoke_app():
    user_id = request.form['user_id']
    name = request.form['name']
    AppUserRelation.delete(name, user_id)
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
