# -*- coding: utf-8 -*-
'''
This module contains all websocket APIs, first thing received will be a json
payload, and then the server will return everything as websocket frames
'''
import json
from flask import g
from json.decoder import JSONDecodeError

from citadel.libs.utils import logger
from citadel.libs.validation import build_args_schema, deploy_schema, remove_container_schema, deploy_elb_schema
from citadel.libs.view import create_api_blueprint
from citadel.models.app import App
from citadel.tasks import celery_task_stream_response, build_image, create_container, remove_container, create_elb_instance


ws = create_api_blueprint('action', __name__, url_prefix='action', jsonize=False, handle_http_error=False)


@ws.route('/build')
def build(socket):
    payload = None
    while not payload or payload.errors:
        message = socket.receive()
        try:
            payload = build_args_schema.loads(message)
            if payload.errors:
                socket.send(json.dumps(payload.errors))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = build_image.delay(args['appname'], args['sha'])
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(json.dumps(m))


@ws.route('/deploy')
def deploy(socket):
    payload = None
    while not payload or payload.errors:
        message = socket.receive()
        try:
            payload = deploy_schema.loads(message)
            if payload.errors:
                socket.send(json.dumps(payload.errors))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

        args = payload.data
        appname = args['appname']
        app = App.get_by_name(appname)
        if not app:
            socket.send(json.dumps({'error': 'app {} not found'.format(appname)}))

        combo_name = args['combo_name']
        combo = app.get_combo(combo_name)
        if not combo:
            socket.send(json.dumps({'error': 'combo {} for app {} not found'.format(combo_name, app)}))

        combo.update(**{k: v for k, v in args.items() if hasattr(combo, k) and v})

    async_result = create_container.delay(zone=g.zone, user_id=g.user_id,
                                          combo_name=combo_name)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(json.dumps(m))


@ws.route('/remove')
def remove(socket):
    payload = None
    while not payload or payload.errors:
        message = socket.receive()
        try:
            payload = remove_container_schema.loads(message)
            if payload.errors:
                socket.send(json.dumps(payload.errors))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = remove_container.delay(zone=g.zone, user_id=g.user_id, **args)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(json.dumps(m))


@ws.route('/deploy-elb')
def deploy_elb(socket):
    payload = None
    while not payload or payload.errors:
        message = socket.receive()
        try:
            payload = deploy_elb_schema.loads(message)
            if payload.errors:
                socket.send(json.dumps(payload.errors))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = create_elb_instance.delay(zone=g.zone, user_id=g.user_id, **args)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(json.dumps(m))
