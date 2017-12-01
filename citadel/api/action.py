# -*- coding: utf-8 -*-
'''
This module contains all websocket APIs, first thing received will be a json
payload, and then the server will return everything as websocket frames
'''
import json
from flask import g
from json.decoder import JSONDecodeError

from citadel.libs.utils import logger
from citadel.libs.validation import build_args_schema, deploy_schema
from citadel.libs.view import create_api_blueprint
from citadel.tasks import celery_task_stream_response, build_image, create_container


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
            payload = build_args_schema.loads(message)
            if payload.errors:
                socket.send(json.dumps(payload.errors))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = create_container.delay(zone=g.zone, user_id=g.user_id, **args)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(json.dumps(m))
