# coding: utf-8
import json
import logging

from flask import g, request, abort, flash

from citadel.action import create_container, remove_container, action_stream, ActionError, upgrade_container
from citadel.config import ELB_APP_NAME
from citadel.libs.utils import to_number, with_appcontext
from citadel.libs.view import create_ajax_blueprint, DEFAULT_RETURN_VALUE
from citadel.models.app import AppUserRelation, Release, App
from citadel.models.container import Container
from citadel.models.env import Environment
from citadel.models.loadbalance import ELBInstance
from citadel.models.oplog import OPType, OPLog
from citadel.rpc import core
from citadel.views.helper import bp_get_app, bp_get_balancer


bp = create_ajax_blueprint('ajax', __name__, url_prefix='/ajax')
log = logging.getLogger(__name__)


@bp.route('/app/<name>/delete-env', methods=['POST'])
def delete_app_env(name):
    envname = request.form['env']
    app = bp_get_app(name)

    # 记录oplog
    OPLog.create(g.user.id, OPType.DELETE_ENV, app.name, content={'envname': envname})

    env = Environment.get_by_app_and_env(app.name, envname)
    if env:
        log.info('Env [%s] for app [%s] deleted', envname, name)
        env.delete()
    return DEFAULT_RETURN_VALUE


@bp.route('/app/<name>/online-entrypoints', methods=['GET'])
def get_app_online_entrypoints(name):
    app = bp_get_app(name)
    return app.get_online_entrypoints()


@bp.route('/app/<name>/online-pods', methods=['GET'])
def get_app_online_pods(name):
    app = bp_get_app(name)
    return app.get_online_pods()


@bp.route('/app/<name>/backends')
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

    if not (release.specs and release.specs.entrypoints):
        abort(404, 'Release %s has no entrypoints')

    podname = request.form['podname']
    entrypoint = request.form['entrypoint']
    count = request.form.get('count', type=int, default=1)
    cpu = request.form.get('cpu', type=int, default=1)
    memory = to_number(request.form.get('memory', default='512MB'))
    envname = request.form.get('envname', '')
    envs = request.form.get('envs', '')
    nodename = request.form.get('nodename', '')
    raw = request.form.get('raw', type=int, default=0)

    if raw and not g.user.privilege:
        abort(400, 'Raw deploy only supported for admins')

    if nodename == '_random':
        nodename = ''
    extra_env = [env.strip() for env in envs.split(';')]
    extra_env = [env for env in extra_env if env]

    # 这里来的就都走自动分配吧
    networks = {key: '' for key in request.form.getlist('networks[]')}

    try:
        print('========networks', networks)
        q = create_container(release.app.git, release.sha, podname, nodename, entrypoint, cpu, memory, count, networks, envname, extra_env, bool(raw))
    except ActionError as e:
        log.error('error when creating container: %s', e.message)
        return {'error': e.message}

    for line in action_stream(q):
        m = json.loads(line)
        if not m['success']:
            log.error('error when creating container: %s', m['error'])
            flash('error when creating container: {}'.format(m['error']))
            continue

    return DEFAULT_RETURN_VALUE


@bp.route('/release/<release_id>/entrypoints')
def get_release_entrypoints(release_id):
    release = Release.get(release_id)
    if not release:
        abort(404, 'Release %s not found' % release_id)

    if not (release.specs and release.specs.entrypoints):
        abort(404, 'Release %s has no entrypoints')

    return release.specs.entrypoints.keys()


@bp.route('/rmcontainer', methods=['POST'])
def remove_containers():
    # 过滤掉ELB的容器, ELB不要走这个方式下线
    container_ids = request.form.getlist('container_id')
    containers = [Container.get_by_container_id(i) for i in container_ids]
    container_ids = [c.container_id for c in containers if c and c.appname != ELB_APP_NAME]

    try:
        q = remove_container(container_ids)
    except ActionError as e:
        log.error('error when removing containers: %s', e.message)
        return {'error': e.message}

    for line in action_stream(q):
        m = json.loads(line)
        if not m['success']:
            log.error('error when deleting container: %s', m['message'])

    return DEFAULT_RETURN_VALUE


@bp.route('/upgrade-container', methods=['POST'])
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
            log.error('error when upgrading container %s: %s', m['id'], m['error'])

    return DEFAULT_RETURN_VALUE


@bp.route('/pods')
def get_all_pods():
    return core.list_pods()


@bp.route('/pod/<name>/nodes')
def get_pod_nodes(name):
    return core.get_pod_nodes(name)


@bp.route('/loadbalance', methods=['POST'])
def create_loadbalance():
    release_id = request.form['releaseid']
    release = Release.get(release_id)
    if not release:
        abort(404, 'Release %s not found' % release_id)

    podname = request.form['podname']
    entrypoint = request.form['entrypoint']
    name = request.form['name']
    cpu = request.form.get('cpu', type=float, default=1)
    nodename = request.form.get('nodename', '')
    comment = request.form.get('comment', '')
    envs = request.form.get('env', '')

    if nodename == '_random':
        nodename = None

    extra_env = ['ELBNAME=%s' % name]
    for env in envs.split(';'):
        env = env.strip()
        if not env:
            continue
        extra_env.append(env)

    try:
        q = create_container(release.app.git, release.sha, podname, nodename, entrypoint, cpu, 0, 1, {}, 'prod', extra_env)
    except ActionError as e:
        log.error('error when creating ELB: %s', e.message)
        return {'error': e.message}

    user_id = g.user.id

    @with_appcontext
    def _stream_consumer(q):
        for line in action_stream(q):
            m = json.loads(line)
            if not m['success']:
                log.error('error when creating ELB: %s', m['error'])
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
        log.info('ELB [%s] created', elb.name)
    return DEFAULT_RETURN_VALUE


@bp.route('/loadbalance/<id>/remove', methods=['POST'])
def remove_loadbalance(id):
    elb = bp_get_balancer(id)
    if elb.is_only_instance():
        elb.clear_rules()

    try:
        q = remove_container([elb.container_id])
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
                log.info('ELB [%s] deleted', elb.name)
                elb.delete()
            else:
                log.error('ELB [%s] delete error, container [%s]', elb.name, m['id'])

    return DEFAULT_RETURN_VALUE


@bp.route('/admin/revoke-app', methods=['POST'])
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
