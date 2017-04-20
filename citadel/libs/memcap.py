# -*- coding: utf-8 -*-

import json
from citadel.models.container import Container
from citadel.rpc import get_core
from citadel.ext import get_etcd
from humanfriendly import parse_size, format_size

MEMORY_RESERVE = parse_size('1GiB', binary=True)
ETCD_CORE_KEY = '/eru-core/pod/{}/node/{}/info'


def get_node_memcap(zone, pod):
    nodes = get_core(zone).get_pod_nodes(pod)
    etcd = get_etcd(zone)

    res = {}
    for node in nodes:
        etcd_data = json.loads(etcd.read(ETCD_CORE_KEY.format(pod, node.name)).value)
        memcap = etcd_data['memcap']
        used_by_memcap = node.memory_total - MEMORY_RESERVE - memcap
        res[node.name] = {
            'total': format_size(node.memory_total, binary=True),
            'used': format_size(node.used_mem, binary=True),
            'used_by_memcap': format_size(used_by_memcap, binary=True),
            'diff': format_size(used_by_memcap - node.used_mem, binary=True),
        }

    return res


def sync_node_memcap(zone, pod):
    nodes = get_core(zone).get_pod_nodes(pod)
    etcd = get_etcd(zone)

    res = {}
    for node in nodes:
        key = ETCD_CORE_KEY.format(pod, node.name)
        etcd_data = json.loads(etcd.read(key).value)
        memcap_by_used = node.memory_total - MEMORY_RESERVE - node.used_mem
        etcd_data['memcap'] = memcap_by_used
        etcd.set(key, json.dumps(etcd_data))
        res[node.name] = format_size(memcap_by_used, binary=True)

    return res
