# -*- coding: utf-8 -*-
"""
run use citadel/bin/run-etcd-watcher
"""
import argparse
import json
import logging

from etcd import EtcdWatchTimedOut, EtcdConnectionFailed

from citadel.config import DEBUG
from citadel.ext import get_etcd
from citadel.app import celery  # must import citadel.app before importing citadel.tasks
from citadel.tasks import deal_with_agent_etcd_change


logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
if DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logging.basicConfig(level=log_level, format='%(levelname)s - %(asctime)s: %(message)s')
logger = logging.getLogger('etcd-watcher')


def watch_etcd(zone=None, etcd_path='/agent2'):
    etcd = get_etcd(zone)
    logger.info('Start watching etcd at zone %s, path %s', zone, etcd_path)
    etcd_index = None
    while True:
        try:
            resp = etcd.watch(etcd_path, recursive=True, timeout=0)
        except (KeyError, EtcdWatchTimedOut, EtcdConnectionFailed):
            continue
        etcd_index = resp.etcd_index
        if not resp or resp.action != 'set':
            continue
        logger.info('Index %s, value %s', etcd_index, resp.value)
        deal_with_agent_etcd_change.delay(resp.key, json.loads(resp.value))


def parse_args():
    parser = argparse.ArgumentParser(description='Watch etcd service, must run in every citadel zone')
    parser.add_argument('zone', help='zone to watch')
    parser.add_argument('-w', '--watch', dest='etcd_path', default='/agent2', help='etcd directory to watch recursively, depend on eru-agent config')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    watch_etcd(zone=args.zone, etcd_path=args.etcd_path)
