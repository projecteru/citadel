# coding: utf-8
from flask import g, request, abort, url_for, redirect
from flask_mako import render_template

from citadel.libs.view import create_page_blueprint
from citadel.models.app import App
from citadel.models.user import get_users, get_user


bp = create_page_blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
def index():
    return redirect(url_for('admin.pods'))


@bp.route('/user')
def users():
    users = get_users(g.start, g.limit, q=request.args.get('q'))
    return render_template('/admin/users.mako', users=users)


@bp.route('/user/<identifier>')
def user_info(identifier):
    user = get_user(identifier)
    if not user:
        abort(404)

    apps = App.get_by_user(user.id)
    all_apps = App.get_all(limit=100)
    all_apps = [app for app in all_apps if app not in apps]
    return render_template('/admin/user_info.mako',
                           user=user,
                           apps=apps,
                           all_apps=all_apps)


@bp.before_request
def access_control():
    if not g.user.privilege:
        abort(403, 'Only for admin')
