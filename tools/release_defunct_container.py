# coding: utf-8

"""
用来修复一些被遗弃的 calico IP.
有时候 docker daemon 挂了, 或者正常停止, calico IP 不会被正常释放.
那么可以用这个脚本修复一下容器所占用的 calico IP.
需要有安装 pycalico 这个包.
需要配置的 etcd 的地址跟 docker / calico 使用的相同, 一般我们都用同一个 etcd 集群, 这个应该不是问题.
"""

import os
import sys

sys.path.append(os.path.abspath('.'))

from netaddr import IPAddress
from pycalico.ipam import IPAMClient
from pycalico.datastore import ETCD_ENDPOINTS_ENV

from citadel.ext import etcd
from citadel.config import ETCD_URL
from citadel.libs.utils import with_appcontext
from citadel.models.container import Container


def get_calico_ipam_client():
    os.environ[ETCD_ENDPOINTS_ENV] = ETCD_URL.replace('etcd', 'http')
    return IPAMClient()


client = get_calico_ipam_client()


@with_appcontext
def fix_defunct_container_networks(container_id):
    c = Container.get_by_container_id(container_id)
    if not c:
        return

    for networkname, network in c.networks.iteritems():
        endpoint_id = network['EndpointID']
        network_id = network['NetworkID']
        ip = IPAddress(network['IPAddress'])

        docker_network_path = '/docker/network/v1.0/endpoint/{}/{}'.format(network_id, endpoint_id)
        calico_network_path = '/calico/v1/host/{}/workload/libnetwork/libnetwork/endpoint/{}'.format(c.nodename, endpoint_id)
        etcd.delete(docker_network_path)
        etcd.delete(calico_network_path)
        client.release_ips({ip})


if __name__ == '__main__':
    container_id = sys.argv[-1]
    fix_defunct_container_networks(container_id)
