# coding: utf-8

from citadel.ext import core
from citadel.views.helper import create_ajax_blueprint


bp = create_ajax_blueprint('core', __name__, url_prefix='/core')


@bp.route('/pods')
def get_pods():
    return core.list_pods()


@bp.route('/pod/<name>/nodes')
def get_pod_nodes(name):
    return core.get_pod_nodes(name)
