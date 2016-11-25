# coding: utf-8
from citadel.app import create_app, make_celery
from citadel.config import DEBUG


app = create_app()
celery = make_celery(app)


if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=DEBUG)
