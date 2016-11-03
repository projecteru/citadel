# coding: utf-8
from citadel import flask_app
from citadel.ext import rds
from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container


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


flask_app.register_blueprint(bp)
