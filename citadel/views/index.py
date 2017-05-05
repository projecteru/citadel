# coding: utf-8
from flask import g, abort, url_for, redirect
from flask_mako import render_template

from citadel.config import CITADEL_HEALTH_CHECK_STATS_KEY
from citadel.ext import rds
from citadel.libs.view import create_page_blueprint
from citadel.models.oplog import OPLog


bp = create_page_blueprint('index', __name__, url_prefix='')


@bp.route('/')
def index():
    return redirect(url_for('app.index'))


@bp.route('/oplog')
def oplog():
    oplogs = OPLog.get_all(g.start, g.limit)
    return render_template('oplog.mako', oplogs=oplogs)


@bp.route('/health-check')
def health_check():
    msg = rds.get(CITADEL_HEALTH_CHECK_STATS_KEY)
    if msg.decode('utf-8') != 'OK':
        abort(500, msg)

    return 'OK'
