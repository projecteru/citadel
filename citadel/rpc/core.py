# coding: utf-8

from __future__ import division
import json
from decimal import Decimal
from urlparse import urlparse
from citadel.libs.json import Jsonized

"""
一些通过grpc从core那边回来的东西, 因为需要被JSON序列化, 所以额外再包一层.
令人伤心, 我还以为可以用 obj.ListFields() 来获取哪些域呢, 结果似乎有些就是不给返回...
先不看这个问题了 = =
TODO: 如果上面的问题解决了, 就可以抛弃这个文件了.
"""


class _CoreRPC(Jsonized):

    fields = []

    def __init__(self, obj):
        for f in self.fields:
            setattr(self, f, getattr(obj, f, None))

    def to_dict(self):
        return {f: getattr(self, f) for f in self.fields}


class Pod(_CoreRPC):

    fields = ['name', 'desc']


class Network(_CoreRPC):

    fields = ['name', 'subnets']

    def __init__(self, network):
        super(Network, self).__init__(network)
        self.subnets = list(network.subnets)

    @property
    def subnets_string(self):
        return ','.join(self.subnets)

    def __str__(self):
        return 'Network<name: %s, subnets: %s>' % (self.name, self.subnets_string)


class Node(_CoreRPC):

    fields = ['name', 'endpoint', 'podname', 'public', 'cpu', 'info', 'available']

    def __init__(self, node):
        super(Node, self).__init__(node)
        self.cpu = dict(node.cpu)
        self.info = node.info and json.loads(node.info) or {}

    @property
    def ip(self):
        u = urlparse(self.endpoint)
        return u.hostname

    @property
    def memory_total(self):
        """memory total in Mib"""
        mem = self.info.get('MemTotal', 0)
        return mem

    @property
    def total_cpu_count(self):
        return self.info.get('NCPU', 0)

    @property
    def containers(self):
        from citadel.models import Container
        containers = Container.get_by_node(self.name, limit=None)
        return containers

    @property
    def used_cpu_count(self):
        return sum([c.cpu_quota for c in self.containers])

    @property
    def used_mem(self):
        mem = sum([c.used_mem for c in self.containers])
        verbose_mem = mem
        return verbose_mem

    @property
    def cpu_count(self):
        return Decimal(sum(v / 10.0 for v in self.cpu.values()))

    def to_dict(self):
        d = super(Node, self).to_dict()
        d['ip'] = self.ip
        d['cpu_count'] = self.cpu_count
        return d


class ErrorDetail(_CoreRPC):

    fields = ['code', 'message']


class BuildImageMessage(_CoreRPC):

    fields = ['status', 'progress', 'error', 'stream', 'error_detail']

    def __init__(self, m):
        super(BuildImageMessage, self).__init__(m)
        self.error_detail = ErrorDetail(self.error_detail)


class CreateContainerMessage(_CoreRPC):

    fields = ['podname', 'nodename', 'id', 'name', 'error', 'success', 'cpu']

    def __init__(self, m):
        super(CreateContainerMessage, self).__init__(m)
        self.cpu = dict(m.cpu)


class RemoveImageMessage(_CoreRPC):

    fields = ['image', 'success', 'messages']


class RemoveContainerMessage(_CoreRPC):

    fields = ['id', 'success', 'message']


class UpgradeContainerMessage(_CoreRPC):

    fields = ['id', 'new_id', 'new_name', 'error', 'success']
