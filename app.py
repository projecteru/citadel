# -*- coding: utf-8 -*-
from citadel import flask_app as app
from citadel.config import DEBUG


if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=DEBUG)
