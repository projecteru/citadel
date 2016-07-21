# -*- coding: utf-8 -*-
import logging

from flask import g
from flask_mako import render_template

from citadel.models import App
from citadel.views.helper import create_page_blueprint, need_login


bp = create_page_blueprint('app', __name__, url_prefix='/app')
log = logging.getLogger(__name__)


@bp.route('/')
def index():
    apps = App.get_by_user(g.user.id, g.start, g.limit)
    return render_template('/app/list.mako', apps=apps)


@bp.before_request
@need_login
def access_control():
    pass
