# -*- coding: utf-8 -*-

from flask import url_for, jsonify, session, request, redirect, Blueprint

from citadel.config import DEFAULT_ZONE, OAUTH_APP_NAME
from citadel.ext import oauth, update_token, delete_token
from citadel.libs.view import DEFAULT_RETURN_VALUE, user_require
from citadel.models.user import User, get_current_user


bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/')
@user_require(True)
def list_users():
    return jsonify([u.to_dict() for u in User.get_all()])


@bp.route('/authorized')
def authorized():
    token = oauth.github.authorize_access_token()
    update_token(OAUTH_APP_NAME, token)
    if not session.get('zone'):
        session['zone'] = DEFAULT_ZONE

    next_url = session.pop('next', None)
    if next_url:
        return redirect(next_url)
    return redirect(url_for('user.login'))


@bp.route('/login')
def login():
    user = get_current_user()
    next_url = request.args.get('next')
    if user:
        if next_url:
            return redirect(next_url)
        return jsonify(user.to_dict())
    redirect_uri = url_for('user.authorized', _external=True)
    session['next'] = next_url
    return oauth.github.authorize_redirect(redirect_uri)


@bp.route('/logout')
def logout():
    delete_token(OAUTH_APP_NAME)
    return DEFAULT_RETURN_VALUE
