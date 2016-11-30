# coding: utf-8
from flask import redirect, url_for

from citadel.libs.view import create_page_blueprint


bp = create_page_blueprint('index', __name__, url_prefix='')


@bp.route('/')
def index():
    return redirect(url_for('app.index'))
