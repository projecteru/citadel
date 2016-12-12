# coding: utf-8
"""
run use citadel/bin/run-etcd-watcher
"""
import json
import logging
import time
from Queue import Queue
from optparse import OptionParser
from thread import get_ident
from threading import Thread

from etcd import EtcdWatchTimedOut, EtcdConnectionFailed
from flask import url_for

from citadel.config import ETCD_URL, DEBUG
from citadel.ext import etcd
from citadel.libs.utils import notbot_sendmsg, with_appcontext
from citadel.models import Container, Release
from citadel.models.loadbalance import update_elb_for_containers, UpdateELBAction
from citadel.publish import publisher


logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
if DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logging.basicConfig(level=log_level, format='%(levelname)s - %(asctime)s: %(message)s')
logger = logging.getLogger('etcd-watcher')
_queue = Queue()
_missing = object()
_jobs = {}
_quit = False


@with_appcontext
def deal(key, data):
    logger.debug('Got etcd data: %s', data)
    global _jobs

    container_id = data.get('ID', '')
    if not container_id:
        return

    ident = get_ident()
    _jobs[ident] = container_id

    try:
        healthy = data.get('Healthy', _missing)
        alive = data.get('Alive', _missing)
        appname = data.get('Name', _missing)
        if _missing in [healthy, alive, appname]:
            return

        container = Container.get_by_container_id(container_id)
        if not container:
            return

        msg = ''
        if healthy:
            logger.info('[%s, %s, %s] ADD [%s] [%s]', container.appname, container.podname, container.entrypoint, container_id, ','.join(container.get_backends()))
            publisher.add_container(container)
            update_elb_for_containers(container)
        else:
            msg = 'Sick container `{}`, checkout {}'.format(container.short_id, url_for('app.app', name=appname, _external=True))

        if not alive:
            logger.info('[%s, %s, %s] REMOVE [%s] from ELB', container.appname, container.podname, container.entrypoint, container_id)
            update_elb_for_containers(container, UpdateELBAction.REMOVE)
            msg = 'Dead container `{}`, checkout {}'.format(container.short_id, url_for('app.app', name=appname, _external=True))

        release = Release.get_by_app_and_sha(container.appname, container.sha)
        subscribers = release.specs.subscribers + ';@timfeirg'
        notbot_sendmsg(subscribers, msg)

        publisher.publish_app(appname)
    finally:
        _jobs.pop(ident, None)


def producer(etcd_path):
    logger.info('Start watching etcd at %s, path %s', ETCD_URL, etcd_path)
    while not _quit:
        try:
            resp = etcd.watch(etcd_path, recursive=True, timeout=0)
        except (KeyError, EtcdWatchTimedOut, EtcdConnectionFailed):
            continue

        if not resp:
            continue

        if resp.action != 'set':
            continue

        try:
            _queue.put((resp.action, resp.key, json.loads(resp.value)))
        except ValueError:
            continue


def consumer():
    logger.info('Start consuming...')
    while not _quit:
        action, key, data = _queue.get()
        logger.info('%s changed', key)

        t = Thread(target=deal, args=(key, data))
        t.daemon = True
        t.start()


def main(etcd_path):
    global _quit, _jobs

    ts = [Thread(target=producer, args=(etcd_path,)), Thread(target=consumer)]
    for t in ts:
        t.daemon = True
        t.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            _quit = True
            break

    t = 0
    while _jobs:
        time.sleep(3)
        t += 3
        logger.info('%d jobs still running', len(_jobs))

        if t >= 30:
            logger.info('30s passed, all jobs quit')
            break
    logger.info('quit')


def get_etcd_path():
    parser = OptionParser()
    parser.add_option('-w', '--watch', dest='etcd_path', default='/agent2', help='etcd directory to watch recursively')
    options, _ = parser.parse_args()
    return options.etcd_path


if __name__ == '__main__':
    etcd_path = get_etcd_path()
    main(etcd_path)
