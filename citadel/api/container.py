# coding: utf-8

from flask import abort
from webargs.flaskparser import use_args

from citadel.libs.validation import GetContainerSchema
from citadel.libs.view import create_api_blueprint, user_require
from citadel.models.container import Container


bp = create_api_blueprint('container', __name__, 'container')


@bp.route('/')
@use_args(GetContainerSchema())
@user_require(False)
def get_by(args):
    cs = Container.get_by(**args)
    return cs


@bp.route('/<container_id>')
@user_require(False)
def get_container(container_id):
    try:
        container = Container.get_by_container_id(container_id)
    except ValueError as e:
        abort(404, str(e))

    if not container:
        abort(404, 'Container not found: {}'.format(container_id))

    return container
