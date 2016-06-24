# -*- coding: utf-8 -*-
from celery import Celery
from flask import jsonify, Flask


def make_celery(app):
    celery = Celery(app.import_name,
                    backend=app.config['CELERY_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app_with_celery():
    app = Flask('citadel')
    app.config.from_object('citadel.config')

    # should be initialized before other imports
    celery = make_celery(app)

    return app, celery

app, celery = create_app_with_celery()


@app.errorhandler(422)
def handle_unprocessable_entity(err):
    # webargs attaches additional metadata to the `data` attribute
    data = getattr(err, 'data')
    if data:
        # Get validations from the ValidationError object
        messages = data['exc'].messages
    else:
        messages = ['Invalid request']

    return jsonify({
        'messages': messages,
    }), 422
