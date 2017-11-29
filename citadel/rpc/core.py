# -*- coding: utf-8 -*-
import json
from decimal import Decimal
from urllib.parse import urlparse

from citadel.libs.jsonutils import Jsonized


"""
The reason for this package:
    * GRPC messages needs to be Jsonized
    * Some entities like Node needs some helper methods
"""


class JSONMessage(Jsonized):

    def __init__(self, obj):
        descriptor_fields = obj.DESCRIPTOR.fields
        self.fields = [f.name for f in descriptor_fields]
        for f in self.fields:
            setattr(self, f, getattr(obj, f, None))

    def to_dict(self):
        return {f: getattr(self, f) for f in self.fields}


class Network(JSONMessage):

    def __init__(self, network):
        super(Network, self).__init__(network)
        self.subnets = list(network.subnets)

    @property
    def subnets_string(self):
        return ','.join(self.subnets)

    def __str__(self):
        return '<{}:{}>' % (self.name, self.subnets_string)


class Node(JSONMessage):

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
        containers = Container.get_by(nodename=self.name, zone=self.zone)
        return containers

    @property
    def used_cpu_count(self):
        return sum([c.cpu_quota for c in self.containers])

    @property
    def used_mem(self):
        mem = sum([c.memory for c in self.containers])
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


class BuildImageMessage(JSONMessage):

    def __init__(self, m):
        super(BuildImageMessage, self).__init__(m)
        self.error_detail = JSONMessage(self.error_detail)


class CreateContainerMessage(JSONMessage):

    def __init__(self, m):
        super(CreateContainerMessage, self).__init__(m)
        self.cpu = dict(m.cpu)
