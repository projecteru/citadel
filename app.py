# coding: utf-8

from citadel.config import DEBUG
from citadel.app import create_app


app = create_app()


if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=DEBUG)
