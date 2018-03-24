# -*- coding: utf-8 -*-

from flask import url_for, jsonify, g, session, request, redirect, Blueprint, abort

from citadel.config import DEFAULT_ZONE, OAUTH_APP_NAME
from citadel.ext import oauth, fetch_token, update_token, delete_token
from citadel.libs.view import DEFAULT_RETURN_VALUE, user_require
from citadel.models.user import User


bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/')
@user_require(True)
def list_users():
    return jsonify([u.to_dict() for u in User.get_all()])


@bp.route('/authorized')
def authorized():
    if session['state'] != request.values.get('state'):
        abort(404, 'Incorrect oauth state')

    params = request.values.to_dict()
    token = oauth.github.fetch_access_token(url_for('user.authorized', _external=True), **params)
    update_token(OAUTH_APP_NAME, token)
    session['user_id'] = g.user.id
    if not session.get('zone'):
        session['zone'] = DEFAULT_ZONE

    next_url = session['next']
    del session['next']
    if next_url:
        return redirect(next_url)
    return redirect(url_for('user.login'))


@bp.route('/login')
def login():
    if fetch_token(OAUTH_APP_NAME):
        return jsonify(g.user.to_dict())
    url, state = oauth.github.generate_authorize_redirect(
        url_for('user.authorized', _external=True)
    )
    session['next'] = request.args.get('next', None)
    session['state'] = state
    return redirect(url)


@bp.route('/logout')
def logout():
    delete_token(OAUTH_APP_NAME)
    return DEFAULT_RETURN_VALUE
