# -*- coding: utf-8 -*-
from flask import g, abort, session, request, Blueprint, jsonify

from citadel.config import DEFAULT_ZONE
from citadel.libs.jsonutils import jsonize
from citadel.libs.view import DEFAULT_RETURN_VALUE, ERROR_CODES
from citadel.models import Container
from citadel.models.app import Release
from citadel.models.elb import update_elb_for_containers, UpdateELBAction
from citadel.models.oplog import OPType, OPLog
from citadel.rpc.client import get_core
from citadel.views.helper import bp_get_app


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
