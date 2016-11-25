# coding: utf-8
from functools import partial

from grpc.beta import implementations
from grpc.framework.interfaces.face.face import AbortionError

from citadel.libs.cache import cache, clean_cache, ONE_DAY
from citadel.libs.utils import handle_exception
from citadel.rpc.core import (Pod, Node, Network, BuildImageMessage,
                              CreateContainerMessage, UpgradeContainerMessage,
                              RemoveContainerMessage)
from citadel.rpc.core_pb2 import (beta_create_CoreRPC_stub, Empty,
                                  AddPodOptions, GetPodOptions,
                                  ListNodesOptions, GetNodeOptions,
                                  AddNodeOptions, BuildImageOptions,
                                  RemoveNodeOptions, DeployOptions,
                                  UpgradeOptions, ContainerID, ContainerIDs)
from citadel.rpc.exceptions import NoStubError


handle_rpc_exception = partial(handle_exception, (NoStubError, AbortionError))
_STREAM_TIMEOUT = 3600
_UNARY_TIMEOUT = 5

_LIST_PODS_KEY = 'citadel:listpods'
_GET_POD = 'citadel:getpod:{name}'
_GET_POD_NODES = 'citadel:getpodnodes:{name}'
_GET_POD_NETWORKS = 'citadel:getpodnetworks:{name}'
_GET_NODE = 'citadel:getnode:{podname}:{nodename}'


class CoreRPC(object):

    def __init__(self, grpc_host, grpc_port):
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port

    def _get_stub(self):
        try:
            channel = implementations.insecure_channel(self.grpc_host, self.grpc_port)
            return beta_create_CoreRPC_stub(channel)
        except Exception as e:
            raise NoStubError(e.message)

    @handle_rpc_exception(default=list)
    def list_pods(self):
        stub = self._get_stub()
        r = stub.ListPods(Empty(), _UNARY_TIMEOUT)
        return [Pod(p) for p in r.pods]

    @handle_rpc_exception(default=None)
    def create_pod(self, name, desc):
        stub = self._get_stub()
        opts = AddPodOptions(name=name, desc=desc)
        p = stub.AddPod(opts, _UNARY_TIMEOUT)

        clean_cache(_LIST_PODS_KEY)
        clean_cache(_GET_POD.format(name=name))
        return p and Pod(p)

    @handle_rpc_exception(default=None)
    def get_pod(self, name):
        stub = self._get_stub()
        opts = GetPodOptions(name=name)
        p = stub.GetPod(opts, _UNARY_TIMEOUT)
        return p and Pod(p)

    @handle_rpc_exception(default=list)
    def get_pod_nodes(self, name):
        stub = self._get_stub()
        opts = ListNodesOptions(podname=name)
        r = stub.ListPodNodes(opts, _UNARY_TIMEOUT)
        return [Node(n) for n in r.nodes]

    @handle_rpc_exception(default=list)
    @cache(_GET_POD_NETWORKS, ttl=ONE_DAY)
    def get_pod_networks(self, name):
        stub = self._get_stub()
        opts = GetPodOptions(name=name)
        r = stub.ListNetworks(opts, _UNARY_TIMEOUT)
        return [Network(n) for n in r.networks]

    @handle_rpc_exception(default=None)
    @cache(_GET_NODE, ttl=ONE_DAY)
    def get_node(self, podname, nodename):
        stub = self._get_stub()
        opts = GetNodeOptions(podname=podname, nodename=nodename)
        n = stub.GetNode(opts, _UNARY_TIMEOUT)
        return n and Node(n)

    @handle_rpc_exception(default=None)
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

    @handle_rpc_exception(default=None)
    def remove_node(self, nodename, podname):
        stub = self._get_stub()
        opts = RemoveNodeOptions(nodename=nodename, podname=podname)

        p = stub.RemoveNode(opts, _UNARY_TIMEOUT)

        clean_cache(_GET_POD_NODES.format(name=podname))
        clean_cache(_GET_NODE.format(podname=podname, nodename=nodename))
        return p and Pod(p)

    @handle_rpc_exception(default=list)
    def build_image(self, repo, version, uid, artifact=''):
        stub = self._get_stub()
        opts = BuildImageOptions(repo=repo, version=version, uid=uid, artifact=artifact)

        for m in stub.BuildImage(opts, _STREAM_TIMEOUT):
            yield BuildImageMessage(m)

    @handle_rpc_exception(default=list)
    def create_container(self, deploy_options):
        stub = self._get_stub()
        opts = DeployOptions(**deploy_options)
        for m in stub.CreateContainer(opts, _STREAM_TIMEOUT):
            yield CreateContainerMessage(m)

    @handle_rpc_exception(default=list)
    def remove_container(self, ids):
        stub = self._get_stub()
        ids = ContainerIDs(ids=[ContainerID(id=i) for i in ids])

        for m in stub.RemoveContainer(ids, _STREAM_TIMEOUT):
            yield RemoveContainerMessage(m)

    @handle_rpc_exception(default=list)
    def upgrade_container(self, ids, image):
        stub = self._get_stub()
        opts = UpgradeOptions(ids=[ContainerID(id=i) for i in ids], image=image)

        for m in stub.UpgradeContainer(opts, _STREAM_TIMEOUT):
            yield UpgradeContainerMessage(m)

    @handle_rpc_exception(default=list)
    def get_containers(self, ids):
        stub = self._get_stub()
        ids = ContainerIDs(ids=[ContainerID(id=i) for i in ids])

        cs = stub.GetContainers(ids, _UNARY_TIMEOUT)
        return [c for c in cs.containers]

    @handle_rpc_exception(default=None)
    def get_container(self, id):
        stub = self._get_stub()
        id = ContainerID(id=id)
        return stub.GetContainer(id, _UNARY_TIMEOUT)
