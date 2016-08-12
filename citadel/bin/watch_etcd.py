# coding: utf-8
"""
run use citadel/bin/run-etcd-watcher
"""
import time
import json
import logging
from threading import Thread
from Queue import Queue
from optparse import OptionParser

from etcd import EtcdWatchTimedOut, EtcdConnectionFailed

from citadel.ext import etcd
from citadel.publish import publisher
from citadel.models import Container
from citadel.models.loadbalance import update_elb_for_containers, UpdateELBAction
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

    if alive:
        _log.info('[%s, %s, %s] ADD [%s] [%s]',
                  container.appname, container.podname,
                  container.entrypoint, container_id,
                  ','.join(container.get_backends()))
        publisher.add_container(container)
        update_elb_for_containers(container)
    else:
        # 嗯这里已经没有办法取到IP了, 只好暂时作罢.
        # 可能可以找个方法把IP给缓存起来.
        _log.info('[%s, %s, %s] REMOVE [%s]',
                  container.appname, container.podname,
                  container.entrypoint, container_id)
        publisher.remove_container(container)
        update_elb_for_containers(container, UpdateELBAction.REMOVE)

    publisher.publish_app(appname)


def producer(etcd_path):
    _log.info('Start watching %s...', etcd_path)
    while True:
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
    _log.info('Start consuming...')
    while True:
        action, key, data = _queue.get()
        _log.info('%s changed', key)

        t = Thread(target=deal, args=(key, data))
        t.daemon = True
        t.start()


def main(etcd_path):
    ts = [Thread(target=producer, args=(etcd_path,)), Thread(target=consumer)]
    for t in ts:
        t.daemon = True
        t.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


def get_etcd_path():
    parser = OptionParser()
    parser.add_option('-w', '--watch', dest='etcd_path', default='/agent2', help='etcd directory to watch recursively')
    options, _ = parser.parse_args()
    return options.etcd_path


if __name__ == '__main__':
    etcd_path = get_etcd_path()
    main(etcd_path)
