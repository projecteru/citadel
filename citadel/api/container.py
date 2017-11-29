# coding: utf-8
from flask import abort, g

from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container


bp = create_api_blueprint('container', __name__, 'container')


@bp.route('/')
def get_all_containers():
    cs = Container.get_all(limit=None)
    return cs


@bp.route('/<container_id>', methods=['GET'])
def get_container(container_id):
    containers = Container.get_by(container_id=container_id, zone=g.zone)
    if not containers:
        abort(404, 'Container not found: {}'.format(container_id))

    if len(containers) != 1:
        abort(400, 'Got multiple containers in zone {}: {}, please use full container_id'.format(g.zone, [str(c) for c in containers]))

    return containers[0]
