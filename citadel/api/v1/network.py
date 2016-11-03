# coding: utf-8
from citadel import flask_app
from citadel.libs.view import create_api_blueprint
from citadel.network.plugin import get_all_pools


bp = create_api_blueprint('network', __name__, 'network')


@bp.route('/', methods=['GET'])
def get_all_networks():
    return get_all_pools()


flask_app.register_blueprint(bp)
