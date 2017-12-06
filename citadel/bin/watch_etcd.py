# -*- coding: utf-8 -*-
"""
run use citadel/bin/run-etcd-watcher
"""
import argparse
import json
import logging

from citadel.app import celery  # must import citadel.app before importing citadel.tasks
from citadel.config import DEBUG, CORE_DEPLOY_INFO_PATH, DEFAULT_ZONE
from citadel.ext import get_etcd
from citadel.tasks import deal_with_agent_etcd_change


_ = celery  # to prevent unused variable
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
if DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logging.basicConfig(level=log_level, format='%(levelname)s - %(asctime)s: %(message)s')
logger = logging.getLogger('etcd-watcher')


def watch_etcd(zone=DEFAULT_ZONE, run_async=True):
    etcd = get_etcd(zone)
    logger.info('Start watching etcd at zone %s, path %s', zone, CORE_DEPLOY_INFO_PATH)
    for resp in etcd.eternal_watch(CORE_DEPLOY_INFO_PATH, recursive=True):
        if not resp or resp.action != 'update' or not resp.value:
            logger.debug('Discard ETCD event: key %s, action %s, value %s', resp.key, resp.action, resp.value)
            continue
        event = json.loads(resp.value)
        if event['Name'] in {'eru', 'lambda'}:
            logger.debug('Discard ETCD event: key %s, value %s', resp.key, resp.value)
            continue
        logger.info('Watch ETCD event: key %s, value %s', resp.key, resp.value)
        if run_async:
            deal_with_agent_etcd_change.delay(resp.key, json.loads(resp.value))
        else:
            deal_with_agent_etcd_change(resp.key, json.loads(resp.value))


def parse_args():
    parser = argparse.ArgumentParser(description='Watch etcd service, must run in every citadel zone')
    parser.add_argument('zone', help='zone to watch')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    watch_etcd(zone=args.zone, etcd_path=args.etcd_path)
