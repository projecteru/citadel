# coding: utf-8

from citadel.libs.mimiron import get_mimiron_containers_for_user
from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container


bp = create_api_blueprint('mimiron', __name__, 'mimiron')


@bp.route('/container/<username>')
def get_containers(username):
    ids = get_mimiron_containers_for_user(username)
    containers = Container.get_by_container_ids(ids)
    return [{'cid': c.container_id, 'appname': c.appname, 'entrypoint': c.entrypoint} for c in containers if c]
