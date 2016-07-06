# coding: utf-8

import sys
import os
sys.path.append(os.path.abspath('.'))

from citadel.app import create_app
from citadel.ext import db
from citadel.models import *


def flushdb(app):
    with app.app_context():
        db.drop_all()
        db.create_all()


if __name__ == '__main__':
    app = create_app()
    dsn = app.config['SQLALCHEMY_DATABASE_URI']
    if '127.0.0.1' in dsn or 'localhost' in dsn or '--force' in sys.argv:
        flushdb(app)
    else:
        print 'you are not doing this on your own computer,'
        print 'if sure, add --force to flush database.'
