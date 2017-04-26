# coding: utf-8
from flask import redirect, url_for, abort

from citadel.config import CITADEL_HEALTH_CHECK_STATS_KEY
from citadel.ext import rds
from citadel.libs.view import create_page_blueprint


bp = create_page_blueprint('index', __name__, url_prefix='')


@bp.route('/')
def index():
    return redirect(url_for('app.index'))


@bp.route('/health-check')
def health_check():
    msg = rds.get(CITADEL_HEALTH_CHECK_STATS_KEY)
    if msg.decode('utf-8') != 'OK':
        abort(500, msg)

    return 'OK'
