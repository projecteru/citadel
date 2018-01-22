# -*- coding: utf-8 -*-
from flask import g, request
from flask_mako import render_template

from citadel.config import ELB_APP_NAME
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, AppUserRelation
from citadel.models.user import User


bp = create_page_blueprint('app_view', __name__, url_prefix='/app')


@bp.route('/')
def index():
    if g.user.privilege and request.values.get('all', type=int):
        apps = [a for a in App.get_all(limit=None) if a.name != ELB_APP_NAME]
    else:
        apps = App.get_by_user(g.user.id)

    return render_template('/app/list.mako', apps=apps)


@bp.route('/<name>/permitted-users', methods=['GET', 'POST'])
def app_permitted_users(name):
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        AppUserRelation.delete(name, user_id)

    user_ids = AppUserRelation.get_user_id_by_appname(name)
    users = [User.get(id_) for id_ in user_ids]
    users = [u for u in users if u]
    return render_template('/app/permitted-users.mako', users=users)
