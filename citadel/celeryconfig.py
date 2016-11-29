# -*- coding: utf-8 -*-
from kombu import Queue
from smart_getenv import getenv

from citadel.config import PROJECT_NAME


timezone = 'Asia/Shanghai'
broker_url = getenv('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
result_backend = getenv('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0')
# if a task isn't acknownledged in 10s, redeliver to another worker
broker_transport_options = {'visibility_timeout': 10}
# rds.nova is used by so many other services, must not interfere
task_default_queue = PROJECT_NAME
task_queues = (
    Queue(PROJECT_NAME, routing_key=PROJECT_NAME),
)
task_default_exchange = PROJECT_NAME
task_default_routing_key = PROJECT_NAME
task_serializer = 'pickle'
accept_content = ['pickle', 'json']
