# -*- coding: utf-8 -*-

from citadel.config import TASK_PUBSUB_CHANNEL, DEBUG, SENTRY_DSN, TASK_PUBSUB_EOF, DEFAULT_ZONE, FAKE_USER
from flask import url_for, jsonify, g, session, request, redirect, Blueprint, abort

from citadel.config import OAUTH_APP_NAME
from citadel.ext import oauth, fetch_token, update_token, delete_token
from citadel.libs.view import DEFAULT_RETURN_VALUE
from citadel.models.user import User


bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/')
def list_users():
    if not g.user.privileged:
        abort(403, 'dude you are not administrator')

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
    delete_token(OAUTH_APP_NAME)
    return DEFAULT_RETURN_VALUE
