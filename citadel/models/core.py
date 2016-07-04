# coding: utf-8

from citadel.utils import Jsonized

"""一些通过grpc从core那边回来的东西, 因为需要被JSON序列化, 所以额外再包一层."""


class Pod(Jsonized):

    def __init__(self, pod):
        self.name = pod.name
        self.desc = pod.desc
        self._pod = pod

    def to_dict(self):
        return {
            'name': self.name,
            'desc': self.desc,
        }


class Node(Jsonized):

    def __init__(self, node):
        self.name = node.name
        self.endpoint = node.endpoint
        self.podname = node.podname
        self.public = node.public
        self.cpu = dict(node.cpu)
        self._node = node

    def to_dict(self):
        return {
            'name': self.name,
            'endpoint': self.endpoint,
            'podname': self.podname,
            'public': self.public,
            'cpu': self.cpu,
        }
