# -*- coding: utf-8 -*-
from operator import attrgetter

import grpc
import wrapt
from grpc import RpcError, StatusCode

from citadel.libs.cache import cache, clean_cache, ONE_DAY
from citadel.libs.utils import logger
from citadel.rpc.core import (Node, Network, BuildImageMessage,
                              CreateContainerMessage, JSONMessage)
from citadel.rpc.core_pb2 import (CoreRPCStub, Empty, NodeAvailable,
                                  AddPodOptions, GetPodOptions,
                                  ListNodesOptions, GetNodeOptions,
                                  AddNodeOptions, BuildImageOptions,
                                  RemoveNodeOptions, DeployOptions,
                                  UpgradeOptions, ContainerID, ContainerIDs,
                                  BackupOptions)


def handle_grpc_exception(default=None):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        try:
            return wrapped(*args, **kwargs)
        except RpcError as e:
            if e.code() is StatusCode.UNAVAILABLE:
                raise
            logger.exception(e)

        return default() if callable(default) else default
    return wrapper


_STREAM_TIMEOUT = 3600
_UNARY_TIMEOUT = 5

_LIST_PODS_KEY = 'citadel:listpods'
_GET_POD = 'citadel:getpod:{name}'
_GET_POD_NODES = 'citadel:getpodnodes:{name}'
_GET_POD_NETWORKS = 'citadel:getpodnetworks:{name}'
_GET_NODE = 'citadel:getnode:{podname}:{nodename}'


class CoreRPC(object):

    def __init__(self, grpc_address):
        self.grpc_address = grpc_address

    def _get_stub(self):
        channel = grpc.insecure_channel(self.grpc_address)
        return CoreRPCStub(channel)

    @handle_grpc_exception(default=list)
    def list_pods(self):
        stub = self._get_stub()
        r = stub.ListPods(Empty(), _UNARY_TIMEOUT)
        return [JSONMessage(p) for p in r.pods]

    @handle_grpc_exception(default=None)
    def create_pod(self, name, desc):
        stub = self._get_stub()
        opts = AddPodOptions(name=name, desc=desc)
        p = stub.AddPod(opts, _UNARY_TIMEOUT)

        clean_cache(_LIST_PODS_KEY)
        clean_cache(_GET_POD.format(name=name))
        return p and JSONMessage(p)

    @handle_grpc_exception(default=None)
    def get_pod(self, name):
        stub = self._get_stub()
        opts = GetPodOptions(name=name)
        p = stub.GetPod(opts, _UNARY_TIMEOUT)
        return p and JSONMessage(p)

    @handle_grpc_exception(default=list)
    def get_pod_nodes(self, name):
        stub = self._get_stub()
        opts = ListNodesOptions(podname=name, all=True)
        r = stub.ListPodNodes(opts, _UNARY_TIMEOUT)
        return sorted([Node(n) for n in r.nodes], key=attrgetter('name'))

    @handle_grpc_exception(default=list)
    @cache(_GET_POD_NETWORKS, ttl=ONE_DAY)
    def get_pod_networks(self, name):
        stub = self._get_stub()
        opts = GetPodOptions(name=name)
        r = stub.ListNetworks(opts, _UNARY_TIMEOUT)
        return [Network(n) for n in r.networks]

    @handle_grpc_exception(default=None)
    @cache(_GET_NODE, ttl=ONE_DAY)
    def get_node(self, podname, nodename):
        stub = self._get_stub()
        opts = GetNodeOptions(podname=podname, nodename=nodename)
        n = stub.GetNode(opts, _UNARY_TIMEOUT)
        return n and Node(n)

    @handle_grpc_exception(default=None)
    def set_node_availability(self, podname, nodename, is_available=True):
        stub = self._get_stub()
        logger.debug('Set node %s:%s available: %s', podname, nodename, is_available)
        opts = NodeAvailable(podname=podname, nodename=nodename, available=is_available)
        n = stub.SetNodeAvailable(opts, _UNARY_TIMEOUT)
        return n and Node(n)

    @handle_grpc_exception(default=None)
    def add_node(self, nodename, endpoint, podname, cafile, certfile, keyfile, public):
        stub = self._get_stub()
        opts = AddNodeOptions(nodename=nodename,
                              endpoint=endpoint,
                              podname=podname,
                              cafile=cafile,
                              certfile=certfile,
                              keyfile=keyfile,
                              public=public)

        n = stub.AddNode(opts, _UNARY_TIMEOUT)

        clean_cache(_GET_POD_NODES.format(name=podname))
        clean_cache(_GET_NODE.format(podname=podname, nodename=nodename))
        return n and Node(n)

    @handle_grpc_exception(default=None)
    def remove_node(self, nodename, podname):
        stub = self._get_stub()
        opts = RemoveNodeOptions(nodename=nodename, podname=podname)

        p = stub.RemoveNode(opts, _UNARY_TIMEOUT)

        clean_cache(_GET_POD_NODES.format(name=podname))
        clean_cache(_GET_NODE.format(podname=podname, nodename=nodename))
        return p and JSONMessage(p)

    @handle_grpc_exception(default=list)
    def build_image(self, repo, version, uid, artifact=''):
        stub = self._get_stub()
        opts = BuildImageOptions(repo=repo, version=version, uid=uid, artifact=artifact)

        for m in stub.BuildImage(opts, _STREAM_TIMEOUT):
            yield BuildImageMessage(m)

    @handle_grpc_exception(default=list)
    def create_container(self, deploy_options):
        stub = self._get_stub()
        deploy_options.pop('zone', None)
        opts = DeployOptions(**deploy_options)
        for m in stub.CreateContainer(opts, _STREAM_TIMEOUT):
            yield CreateContainerMessage(m)

    @handle_grpc_exception(default=list)
    def remove_container(self, ids):
        stub = self._get_stub()
        ids = ContainerIDs(ids=[ContainerID(id=i) for i in ids])

        for m in stub.RemoveContainer(ids, _STREAM_TIMEOUT):
            yield JSONMessage(m)

    def backup(self, id_, src_path):
        stub = self._get_stub()
        opts = BackupOptions(id=id_, src_path=src_path)
        msg = stub.Backup(opts, _STREAM_TIMEOUT)
        return msg and JSONMessage(msg)

    @handle_grpc_exception(default=list)
    def upgrade_container(self, ids, image):
        stub = self._get_stub()
        opts = UpgradeOptions(ids=[ContainerID(id=i) for i in ids], image=image)

        for m in stub.UpgradeContainer(opts, _STREAM_TIMEOUT):
            yield JSONMessage(m)

    @handle_grpc_exception(default=list)
    def get_containers(self, ids):
        stub = self._get_stub()
        ids = ContainerIDs(ids=[ContainerID(id=i) for i in ids])

        cs = stub.GetContainers(ids, _UNARY_TIMEOUT)
        return [c for c in cs.containers]

    @handle_grpc_exception(default=None)
    def get_container(self, id):
        stub = self._get_stub()
        id = ContainerID(id=id)
        return stub.GetContainer(id, _UNARY_TIMEOUT)
