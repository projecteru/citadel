# -*- coding: utf-8 -*-
from flask import g, abort, session, request, Blueprint, jsonify

from citadel.config import DEFAULT_ZONE
from citadel.libs.jsonutils import jsonize
from citadel.libs.view import DEFAULT_RETURN_VALUE, ERROR_CODES
from citadel.models import Container
from citadel.models.elb import update_elb_for_containers, UpdateELBAction


bp = Blueprint('ajax', __name__, url_prefix='/ajax')


def _error_hanlder(error):
    return jsonify({'error': error.description}), error.code


for code in ERROR_CODES:
    bp.errorhandler(code)(_error_hanlder)


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
