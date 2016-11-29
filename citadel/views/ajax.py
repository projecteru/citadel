# -*- coding: utf-8 -*-
import json

from flask import Blueprint, jsonify, Response, g, request, abort, flash

from citadel.config import CONTAINER_DEBUG_LOG_CHANNEL, ELB_APP_NAME, ELB_POD_NAME
from citadel.ext import rds
from citadel.libs.json import jsonize
from citadel.libs.utils import logger, to_number, with_appcontext
from citadel.libs.view import DEFAULT_RETURN_VALUE, ERROR_CODES
from citadel.models.app import AppUserRelation, Release, App
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.loadbalance import ELBInstance
from citadel.models.oplog import OPType, OPLog
from citadel.rpc import core
from citadel.tasks import create_container, remove_container, ActionError, upgrade_container, action_stream, celery_task_stream_response
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

    # 记录oplog
    OPLog.create(g.user.id, OPType.DELETE_ENV, app.name, content={'envname': envname})

    env = Environment.get_by_app_and_env(app.name, envname)
    if env:
        logger.info('Env [%s] for app [%s] deleted', envname, name)
        env.delete()
    return DEFAULT_RETURN_VALUE


@bp.route('/app/<name>/online-entrypoints', methods=['GET'])
@jsonize
def get_app_online_entrypoints(name):
    app = bp_get_app(name)
    return app.get_online_entrypoints()


@bp.route('/app/<name>/online-pods', methods=['GET'])
@jsonize
def get_app_online_pods(name):
    app = bp_get_app(name)
    return app.get_online_pods()


@bp.route('/app/<name>/backends')
@jsonize
def get_app_backends(name):
    return {}


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

    # TODO: args validation
    payload = request.get_json()
    appname = release.name
    envname = payload.get('envname', '')
    full_envs = Environment.get_by_app_and_env(appname, envname)
    full_envs = full_envs and full_envs.to_env_vars() or []
    extra_env = [env.strip() for env in payload.get('extra_env', '').split(';')]
    extra_env = [env for env in extra_env if env]
    full_envs.extend(extra_env)
    # 这里来的就都走自动分配吧
    networks = {key: '' for key in payload['networks']}
    debug = payload.get('debug', False)
    raw = payload.get('raw', False)
    if raw and not g.user.privilege:
        abort(400, 'Raw deploy only supported for admins')

    deploy_options = {
        'specs': release.specs_text,
        'appname': appname,
        'image': specs.base if raw else release.image,
        'podname': payload['podname'],
        'nodename': payload.get('nodename', ''),
        'entrypoint': payload['entrypoint'],
        'cpu_quota': float(payload.get('cpu', 1)),
        'count': int(payload.get('count', 1)),
        'memory': to_number(payload.get('memory', '512MB')),
        'networks': networks,
        'env': full_envs,
        'raw': raw,
        'debug': debug,
    }

    logger.debug('Start celery create_container task with payload: %s', deploy_options)
    async_result = create_container.delay(deploy_options=deploy_options,
                                          sha=release.sha,
                                          envname=envname,
                                          user_id=g.user.id)

    def generate_stream_response():
        """relay grpc message, if in debug mode, stream logs as well"""
        for msg in celery_task_stream_response(async_result.task_id):
            yield msg

        async_result.wait(timeout=20)
        if async_result.failed():
            logger.debug('Task %s failed, dumping traceback', async_result.task_id)
            yield json.dumps({'error': async_result.traceback})

        if debug:
            debug_log_channel = CONTAINER_DEBUG_LOG_CHANNEL.format(release.name)
            debug_log_pubsub = rds.pubsub()
            debug_log_pubsub.psubscribe(debug_log_channel)
            for item in debug_log_pubsub.listen():
                logger.debug('Stream response emit debug log: %s', item)
                yield json.dumps(item)

    return Response(generate_stream_response(), mimetype='application/json')


@bp.route('/release/<release_id>/entrypoints')
@jsonize
def get_release_entrypoints(release_id):
    release = Release.get(release_id)
    if not release:
        abort(404, 'Release %s not found' % release_id)

    if not (release.specs and release.specs.entrypoints):
        abort(404, 'Release %s has no entrypoints')

    return release.specs.entrypoints.keys()


@bp.route('/rmcontainer', methods=['POST'])
@jsonize
def remove_containers():
    # 过滤掉ELB的容器, ELB不要走这个方式下线
    raw_container_ids = request.form.getlist('container_id')
    raw_containers = [Container.get_by_container_id(i) for i in raw_container_ids]
    containers = [c for c in raw_containers if c and c.appname != ELB_APP_NAME]
    container_ids = [c.container_id for c in containers]
    # mark removing so that users would see some changes, but the actual
    # removing happends in celery tasks
    for c in containers:
        c.mark_removing()

    remove_container.delay(container_ids, user_id=g.user.id)
    return DEFAULT_RETURN_VALUE


@bp.route('/upgrade-container', methods=['POST'])
@jsonize
def upgrade_containers():
    container_ids = request.form.getlist('container_id')
    sha = request.form['sha']
    appname = request.form['appname']

    app = App.get_by_name(appname)
    if not app:
        abort(400, 'App %s not found' % appname)
    if app.name == ELB_APP_NAME:
        abort(400, 'Do not upgrade %s through this API' % ELB_APP_NAME)

    try:
        q = upgrade_container(container_ids, app.git, sha)
    except ActionError as e:
        return {'error': e.message}

    for line in action_stream(q):
        m = json.loads(line)
        if not m['success']:
            logger.error('error when upgrading container %s: %s', m['id'], m['error'])

    return DEFAULT_RETURN_VALUE


@bp.route('/pods')
@jsonize
def get_all_pods():
    return core.list_pods()


@bp.route('/pod/<name>/nodes')
@jsonize
def get_pod_nodes(name):
    return core.get_pod_nodes(name)


@bp.route('/loadbalance', methods=['POST'])
@jsonize
def create_loadbalance():
    release_id = request.form['releaseid']
    release = Release.get(release_id)
    if not release:
        abort(404, 'Release %s not found' % release_id)

    entrypoint = request.form['entrypoint']
    cpu = request.form.get('cpu', type=float, default=1)
    nodename = request.form.get('nodename', '')
    comment = request.form.get('comment', '')
    envname = request.form['envname']
    env = Environment.get_by_app_and_env(ELB_APP_NAME, envname)
    name = env.get('ELBNAME', 'unnamed')
    memory = to_number('2GB')

    try:
        q = create_container(release.app.git, release.sha, ELB_POD_NAME, nodename, entrypoint, cpu, memory, 1, {}, envname)
    except ActionError as e:
        msg = 'error when creating ELB: %s', e.message
        logger.error(msg)
        flash(msg)
        return {'error': e.message}

    user_id = g.user.id

    @with_appcontext
    def _stream_consumer(q):
        for line in action_stream(q):
            m = json.loads(line)
            if not m['success']:
                logger.error('error when creating ELB: %s', m['error'])
                continue

            container = Container.get_by_container_id(m['id'])
            if not container:
                continue

            ips = container.get_ips()
            elb = ELBInstance.create(ips[0], container.container_id, name, comment)

            # 记录oplog
            op_content = {'elbname': name, 'container_id': container.container_id}
            OPLog.create(user_id, OPType.CREATE_ELB_INSTANCE, release.app.name, release.sha, op_content)

            yield elb

    for elb in _stream_consumer(q):
        logger.info('ELB [%s] created', elb.name)
    return DEFAULT_RETURN_VALUE


@bp.route('/loadbalance/<id>/remove', methods=['POST'])
@jsonize
def remove_loadbalance(id):
    elb = bp_get_balancer(id)
    if elb.is_only_instance():
        elb.clear_rules()

    try:
        q = remove_container([elb.container_id], user_id=g.user.id)
    except ActionError as e:
        return {'error': e.message}

    if q.empty():
        # sometimes life is hard, container may already be deleted, but not in
        # citadel, so the queue is empty
        elb.delete()
    else:
        for line in action_stream(q):
            m = json.loads(line)
            if m['success'] and elb.container_id == m['id']:
                logger.info('ELB [%s] deleted', elb.name)
                elb.delete()
            else:
                logger.error('ELB [%s] delete error, container [%s]', elb.name, m['id'])

    return DEFAULT_RETURN_VALUE


@bp.route('/admin/revoke-app', methods=['POST'])
@jsonize
def revoke_app():
    user_id = request.form['user_id']
    name = request.form['name']
    AppUserRelation.delete(name, user_id)
    return DEFAULT_RETURN_VALUE


@bp.before_request
def access_control():
    # loadbalance和admin的不是admin就不要乱搞了
    if not g.user.privilege and (request.path.startswith('/ajax/admin') or request.path.startswith('/ajax/loadbalance')):
        abort(403, 'Only for admin')
