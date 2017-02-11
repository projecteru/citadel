# -*- coding: utf-8 -*-
from flask import request, abort
from requests.exceptions import HTTPError

from citadel.libs.agent import EruAgentClient, list_vip_from_redis, generate_vip
from citadel.libs.view import create_api_blueprint, DEFAULT_RETURN_VALUE


bp = create_api_blueprint('virtualip', __name__, 'virtualip')


@bp.route('/set', methods=['POST'])
def set_vip():
    data = request.get_json()
    vip = data.get('vip')
    node = data.get('node')
    if not node:
        abort(400, 'Missing node')

    if not vip:
        try:
            vip = generate_vip()
        except KeyError as e:
            return {'error': 'No available vip'}, 500

    client = EruAgentClient(node)
    try:
        client.set_vip(vip)
    except HTTPError as e:
        return {'error': str(e)}, e.response.status_code

    return DEFAULT_RETURN_VALUE


@bp.route('/del', methods=['POST'])
def del_vip():
    data = request.get_json()
    node = data.get('node')
    vip = data.get('vip')
    if not node or not vip:
        abort(400, 'Missing node/vip')

    client = EruAgentClient(node)
    if not client.exists_vip(vip):
        abort(400, 'Vip not exists')

    try:
        client.del_vip(vip)
    except HTTPError as e:
        return {'error': str(e)}, e.response.status_code

    return DEFAULT_RETURN_VALUE


@bp.route('/migrate', methods=['POST'])
def migrate_vip():
    data = request.get_json()
    from_node = data.get('from')
    to_node = data.get('to')
    vip = data.get('vip')

    if not from_node or not to_node or not vip:
        abort(400, 'Missing from/to/vip')

    from_client = EruAgentClient(from_node)
    if not from_client.exists_vip(vip):
        abort(400, 'Vip do not exists in {}'.format(from_node))

    to_client = EruAgentClient(to_node)
    if to_client.exists_vip(vip):
        abort(400, 'Vip already exists in {}'.format(to_node))

    try:
        from_client.del_vip(vip)
    except HTTPError as e:
        return {'error': str(e)}, e.response.status_code

    try:
        to_client.set_vip(vip)
    except HTTPError as e:
        return {'error': str(e)}, e.response.status_code

    return DEFAULT_RETURN_VALUE


@bp.route('/list', methods=['GET'])
def list_vip():
    return list_vip_from_redis()
