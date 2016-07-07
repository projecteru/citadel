# coding: utf-8
from flask import abort
from webargs import fields, ValidationError
from webargs.flaskparser import use_args

from citadel.ext import core
from citadel.libs.view import create_api_blueprint
from citadel.models.app import App, Release
from citadel.models.container import Container


bp = create_api_blueprint('container', __name__, 'container')


@bp.route('/<container_id>', methods=['GET'])
def get_container(container_id):
    c = Container.get_by_container_id(container_id)
    if not c:
        abort(404, 'container `%s` not found' % container_id)
    return c


def _get_app_by_name(appname):
    app = App.get_by_name(appname)
    if not app:
        raise ValidationError('no valid address')
    return app


_deploy_args = {
    'appname': fields.Function(required=True, deserialize=_get_app_by_name),
    'podname': fields.Str(required=True),
    'cpu_quota': fields.Int(missing=1),
    'ncontainer': fields.Int(missing=1),
    'sha': fields.Str(required=True),
    'entrypoint': fields.Str(required=True),
    'env': fields.Str(required=True),
}


@bp.route('/add', methods=['POST'])
@use_args(_deploy_args)
def create_container(args):
    app = args['app']
    appname, specs = app.specs, app.name
    release = Release.get_by_app_and_sha(appname, args['sha'])
    # TODO: unfinished
    # TODO: networks 不知道怎么搞，是复用 eru-core 的 networks 部分吗？
    # TODO: pod 要抄吗？之前 eru-core 的 deploy 需要搞那个 nshare，但是 corerpc
    # 里边貌似不需要额
    core.create_container(specs, appname, release.image, args['podname'],
                          args['entrypoint'], args['cpu_quota'], args['ncontainer'], )
