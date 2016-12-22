# -*- coding: utf-8 -*-
import json

from citadel.ext import etcd
from citadel.libs.utils import handle_etcd_exception
from citadel.rpc import core


@handle_etcd_exception(default=list)
def get_all_pools():
    """如果是用network插件, 直接读docker的就好了.
    为什么不用docker的API走gRPC过来呢, 因为麻烦.
    哪位好汉之后有心可以改走docker的API, 害得随机取个node, 麻烦"""

    def _parse_docker_network(data):
        r = json.loads(data)
        if r.get('ipamV4Info'):
            r['ipamV4Info'] = json.loads(r['ipamV4Info'])
            for k in r['ipamV4Info']:
                if k.get('IPAMData'):
                    k['IPAMData'] = json.loads(k['IPAMData'])
        if r.get('ipamV4Config'):
            r['ipamV4Config'] = json.loads(r['ipamV4Config'])
        return r

    r = etcd.get('/docker/network/v1.0/network')
    return [_parse_docker_network(n.value) for n in r.children]


def get_all_networks(podname):
    return core.get_pod_networks(podname)
