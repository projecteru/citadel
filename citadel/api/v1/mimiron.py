# coding: utf-8

from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container
from citadel.ext import rds


bp = create_api_blueprint('mimiron', __name__, 'mimiron')

@bp.route('/container/<username>')
def get_containers(username):
    key = 'mimiron:{}:route'.format(username)
    cids =  rds.hkeys(key)

    res = []
    for cid in cids:
        info = Container.get_by_container_id(cid)
        res.append({
            'cid': cid,
            'appname': info.appname,
            'entrypoint': info.entrypoint
        })
    return res
