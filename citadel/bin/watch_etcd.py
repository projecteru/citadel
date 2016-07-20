# coding: utf-8

import time
import json
import logging
from threading import Thread
from Queue import Queue

from etcd import EtcdWatchTimedOut, EtcdConnectionFailed

from citadel.ext import etcd
from citadel.publish import publisher
from citadel.models import Container
from citadel.libs.utils import with_appcontext


logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s: %(message)s')
_log = logging.getLogger(__name__)
_queue = Queue()
_missing = object()


@with_appcontext
def deal(key, data):
    container_id = data.get('ID', '')
    if not container_id:
        return

    alive = data.get('Alive', _missing)
    if alive is _missing:
        return

    appname = data.get('Name', _missing)
    if appname is _missing:
        return

    container = Container.get_by_container_id(container_id)
    if not container:
        return

    # TODO
    # 这里需要改下, 应该是从balancer直接剔除这个节点比较简单
    if alive:
        _log.info('add')
        publisher.add_container(container)
    else:
        _log.info('remove')
        publisher.remove_container(container)
    publisher.publish_app(appname)


def producer():
    _log.info('start watching...')
    while True:
        try:
            resp = etcd.watch('/agent2', recursive=True, timeout=0)
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
    _log.info('start consuming...')
    while True:
        action, key, data = _queue.get()
        _log.info('%s changed' % key)

        t = Thread(target=deal, args=(key, data))
        t.daemon = True
        t.start()


def main():
    ts = [Thread(target=producer), Thread(target=consumer)]
    for t in ts:
        t.daemon = True
        t.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    main()
