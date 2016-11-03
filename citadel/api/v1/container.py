# coding: utf-8
from flask import abort

from citadel import flask_app
from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container


bp = create_api_blueprint('container', __name__, 'container')


@bp.route('/<container_id>', methods=['GET'])
def get_container(container_id):
    c = Container.get_by_container_id(container_id)
    if not c:
        abort(404, 'Container not found: {}'.format(container_id))
    return c


flask_app.register_blueprint(bp)
