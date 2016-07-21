# -*- coding: utf-8 -*-
from flask import redirect, url_for
from citadel.views.helper import create_page_blueprint, need_login

bp = create_page_blueprint('index', __name__, url_prefix='')


@bp.route('/')
def index():
    return redirect(url_for('app.index'))


@bp.before_request
@need_login
def access_control():
    pass

