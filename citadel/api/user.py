# -*- coding: utf-8 -*-

from flask import url_for, jsonify, g, session, request, redirect, Blueprint, abort

from citadel.config import OAUTH_APP_NAME
from citadel.ext import oauth, fetch_token, update_token


bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/authorized')
def authorized():
    if session['state'] != request.values.get('state'):
        abort(404, 'Incorrect oauth state')

    params = request.values.to_dict()
    token = oauth.github.fetch_access_token(url_for('user.authorized', _external=True), **params)
    update_token(OAUTH_APP_NAME, token)
    return redirect(url_for('user.login'))


@bp.route('/login')
def login():
    if fetch_token(OAUTH_APP_NAME):
        return jsonify(g.user.to_dict())
    url, state = oauth.github.generate_authorize_redirect(
        url_for('user.authorized', _external=True)
    )
    session['state'] = state
    return redirect(url)


@bp.route('/logout')
def logout():
    session.pop('sso', None)
    return redirect(url_for('index.index'))
