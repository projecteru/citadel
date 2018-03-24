# -*- coding: utf-8 -*-
'''
Action APIs using websocket, upon connection, client should send a first json
payload, and then server will work and steam the output as websocket frames
'''

import json
from flask import session
from json.decoder import JSONDecodeError
from marshmallow import ValidationError

from citadel.libs.utils import logger
from citadel.libs.validation import renew_schema, build_args_schema, deploy_schema, remove_container_schema, deploy_elb_schema
from citadel.libs.view import create_api_blueprint, user_require
from citadel.models.app import App
from citadel.models.container import Container
from citadel.tasks import renew_container, celery_task_stream_response, build_image, create_container, remove_container, create_elb_instance


ws = create_api_blueprint('action', __name__, url_prefix='action', jsonize=False, handle_http_error=False)


@ws.route('/build')
@user_require(False)
def build(socket):
    """Build an image for the specified release, the API will return all docker
    build messages, key frames as shown in the example responses

    :<json string appname: required, the app name
    :<json string sha: required, minimum length is 7

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "id": "",
            "status": "",
            "progress": "",
            "error": "",
            "stream": "Step 1/7 : FROM python:latest as make-artifacts",
            "error_detail": {
                "code": 0,
                "message": "",
                "__class__": "ErrorDetail"
            },
            "__class__": "BuildImageMessage"
        }

        {
        "id": "0179a75e26fe",
        "status": "Pushing",
        "progress": "[==================================================>]  6.656kB",
        "error": "",
        "stream": "",
        "error_detail": {
            "code": 0,
            "message": "",
            "__class__": "ErrorDetail"
        },
        "__class__": "BuildImageMessage"
        }

        {
        "id": "",
        "status": "finished",
        "progress": "hub.ricebook.net/projecteru2/test-app:3641aca",
        "error": "",
        "stream": "finished hub.ricebook.net/projecteru2/test-app:3641aca",
        "error_detail": {
            "code": 0,
            "message": "",
            "__class__": "ErrorDetail"
        },
        "__class__": "BuildImageMessage"
        }

    """
    payload = None
    while True:
        message = socket.receive()
        try:
            payload = build_args_schema.loads(message)
            break
        except ValidationError as e:
            socket.send(json.dumps(e.messages))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = build_image.delay(args['appname'], args['sha'])
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(m)


@ws.route('/deploy')
@user_require(False)
def deploy(socket):
    """Create containers for the specified release

    :<json string appname: required
    :<json string zone: required
    :<json string sha: required, minimum length is 7
    :<json string combo_name: required, specify the combo to use, you can
    update combo value using this API, so all parameters in the
    :http:post:`/api/app/(appname)/combo` are supported

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "podname": "eru",
            "nodename": "c1-eru-2.ricebook.link",
            "id": "9c91d06cb165e829e8e0ad5d5b5484c47d4596af04122489e4ead677113cccb4",
            "name": "test-app_web_kMqYFQ",
            "error": "",
            "success": true,
            "cpu": {"0": 20},
            "quota": 0.2,
            "memory": 134217728,
            "publish": {"bridge": "172.17.0.5:6789"},
            "hook": "I am the hook output",
            "__class__": "CreateContainerMessage"
        }

    """
    payload = None
    while True:
        message = socket.receive()
        try:
            payload = deploy_schema.loads(message)
            break
        except ValidationError as e:
            socket.send(json.dumps(e.messages))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    appname = args['appname']
    app = App.get_by_name(appname)
    if not app:
        socket.send(json.dumps({'error': 'app {} not found'.format(appname)}))
        socket.close()

    combo_name = args['combo_name']
    combo = app.get_combo(combo_name)
    if not combo:
        socket.send(json.dumps({'error': 'combo {} for app {} not found'.format(combo_name, app)}))
        socket.close()

    combo.update(**{k: v for k, v in args.items() if hasattr(combo, k)})

    async_result = create_container.delay(user_id=session.get('user_id'),
                                          **args)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(m)


@ws.route('/renew')
@user_require(False)
def renew(socket):
    """Create a new container to substitute the old one, this API can be used
    to upgrade a app to a specified version, or simply re-create a container
    using the same combo.

    Things can go wrong at any step, the example response
    was the output generated by ``renew("1aa8a638a153b393ee423c0a8c158757b13ab74591ade036b6e73ac33a4bdeac", "3641aca")``
    which failed because the newly created container didn't become healthy
    within the given time limit.

    :<json list container_ids: required, a list of container_id
    :<json string sha: required, minimum length is 7

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "podname": "eru",
            "nodename": "c1-eru-2.ricebook.link",
            "id": "2f123f1abcdfc8208b298c89e10bcd8f48f9fdb25c9eb7874ea5cc7199825e6e",
            "name": "test-app_web_rvrhPg",
            "error": "",
            "success": true,
            "cpu": {"0": 20},
            "quota": 0.2,
            "memory": 134217728,
            "publish": {"bridge": "172.17.0.5:6789"},
            "hook": "hook output",
            "__class__": "CreateContainerMessage"
        }

        {
            "id": "2f123f1abcdfc8208b298c89e10bcd8f48f9fdb25c9eb7874ea5cc7199825e6e",
            "success": true,
            "message": "hook output",
            "__class__": "RemoveContainerMessage"
        }

        {
            "error": "New container <Container test-zone:test-app:3641aca:web:2f123f1 did't became healthy, remove result: id: 2f123f1abcdfc8208b298c89e10bcd8f48f9fdb25c9eb7874ea5cc7199825e6e success: true",
            "args": ["1aa8a638a153b393ee423c0a8c158757b13ab74591ade036b6e73ac33a4bdeac", "3641aca"],
            "kwargs": {"user_id": null}
        }

    """
    payload = None
    while True:
        message = socket.receive()
        try:
            payload = renew_schema.loads(message)
            break
        except ValidationError as e:
            socket.send(json.dumps(e.messages))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    containers = [Container.get_by_container_id(id_) for id_ in args['container_ids']]
    appnames = {c.appname for c in containers}
    sha = args['sha']
    if len(appnames) >1 and sha:
        socket.send(json.dumps({'error': 'cannot provide sha when renewing containers of multiple apps: {}'.format(appnames)}))
        socket.close()

    appname = appnames.pop()
    app = App.get_by_name(appname)
    if not app:
        socket.send(json.dumps({'error': 'app {} not found'.format(appname)}))
        socket.close()

    task_ids = []
    for c in containers:
        async_result = renew_container.delay(c.container_id, sha,
                                             user_id=session.get('user_id'))
        task_ids.append(async_result.task_id)

    for m in celery_task_stream_response(task_ids):
        logger.debug(m)
        socket.send(m)


@ws.route('/remove')
@user_require(False)
def remove(socket):
    """Remove the specified containers

    :<json list container_ids: required, a list of container_id

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "id": "9c91d06cb165e829e8e0ad5d5b5484c47d4596af04122489e4ead677113cccb4",
            "success": true,
            "message": "hook output",
            "__class__": "RemoveContainerMessage"
        }

    """
    payload = None
    while True:
        message = socket.receive()
        try:
            payload = remove_container_schema.loads(message)
            break
        except ValidationError as e:
            socket.send(json.dumps(e.messages))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = remove_container.delay(user_id=session.get('user_id'), **args)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(m)


@ws.route('/deploy-elb')
@user_require(True)
def deploy_elb(socket):
    """Remove the specified containers

    :<json string name: required, ELB cluster name
    :<json string zone: required
    :<json string sha: required, minimum length is 7
    :<json string combo_name: required, the combo used to create ELB containers
    :<json string nodename: optional

    """
    payload = None
    while True:
        message = socket.receive()
        try:
            payload = deploy_elb_schema.loads(message)
            break
        except ValidationError as e:
            socket.send(json.dumps(e.messages))
        except JSONDecodeError as e:
            socket.send(json.dumps({'error': str(e)}))

    args = payload.data
    async_result = create_elb_instance.delay(user_id=session.get('user_id'),
                                             **args)
    for m in celery_task_stream_response(async_result.task_id):
        logger.debug(m)
        socket.send(m)
