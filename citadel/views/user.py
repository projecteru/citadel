# -*- coding: utf-8 -*-
from flask import session, Blueprint, redirect, url_for, abort
from flask import g

from citadel.ext import sso
from citadel.libs.utils import login_logger


bp = Blueprint('user', __name__, url_prefix='/user')


@sso.tokengetter
def get_oauth_token():
    token = session.get('sso')
    login_logger.info('[%s] get_oauth_token get token %s', g.seed, token)
    return token, ''


@bp.route('/authorized')
def authorized():
    resp = sso.authorized_response()
    if resp is None:
        abort(400)

    session['sso'] = resp['access_token']
    return redirect(url_for('user.login'))


@bp.route('/login')
def login():
    if 'sso' in session:
        return redirect(url_for('index.index'))
    return sso.authorize(callback=url_for('user.authorized', _external=True))


@bp.route('/logout')
def logout():
    session.pop('sso', None)
    return redirect(url_for('index.index'))
