# coding: utf-8
from functools import partial

from grpc.beta import implementations
from grpc.framework.interfaces.face.face import AbortionError

import citadel.rpc.core_pb2 as pb
from citadel.libs.utils import handle_exception
from citadel.rpc.exceptions import NoStubError
from citadel.rpc.core import (Pod, Node, BuildImageMessage,
        CreateContainerMessage, UpgradeContainerMessage, RemoveContainerMessage)


handle_rpc_exception = partial(handle_exception, (NoStubError, AbortionError))
_STREAM_TIMEOUT = 3600
_UNARY_TIMEOUT = 5


class CoreRPC(object):

    def __init__(self, grpc_host, grpc_port):
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port

    def _get_stub(self):
        try:
            channel = implementations.insecure_channel(self.grpc_host, self.grpc_port)
            return pb.beta_create_CoreRPC_stub(channel)
        except Exception as e:
            raise NoStubError(e.message)

    @handle_rpc_exception(default=list)
    def list_pods(self):
        stub = self._get_stub()
        r = stub.ListPods(pb.Empty(), _UNARY_TIMEOUT)
        return [Pod(p) for p in r.pods]

    @handle_rpc_exception(default=None)
    def create_pod(self, name, desc):
        stub = self._get_stub()
        opts = pb.AddPodOptions(name=name, desc=desc)
        p = stub.AddPod(opts, _UNARY_TIMEOUT)
        return p and Pod(p)

    @handle_rpc_exception(default=None)
    def get_pod(self, name):
        stub = self._get_stub()
        opts = pb.GetPodOptions(name=name)
        p = stub.GetPod(opts, _UNARY_TIMEOUT)
        return p and Pod(p)

    @handle_rpc_exception(default=list)
    def get_pod_nodes(self, name):
        stub = self._get_stub()
        opts = pb.ListNodesOptions(podname=name)
        r = stub.ListPodNodes(opts, _UNARY_TIMEOUT)
        return [Node(n) for n in r.nodes]

    @handle_rpc_exception(default=None)
    def get_node(self, podname, nodename):
        stub = self._get_stub()
        opts = pb.GetNodeOptions(podname=podname, nodename=nodename)
        n = stub.GetNode(opts, _UNARY_TIMEOUT)
        return n and Node(n)

    @handle_rpc_exception(default=None)
    def add_node(self, nodename, endpoint, podname, cafile, certfile, keyfile, public):
        stub = self._get_stub()
        opts = pb.AddNodeOptions(nodename=nodename,
                                 endpoint=endpoint,
                                 podname=podname,
                                 cafile=cafile,
                                 certfile=certfile,
                                 keyfile=keyfile,
                                 public=public)

        n = stub.AddNode(opts, _UNARY_TIMEOUT)
        return n and Node(n)

    @handle_rpc_exception(default=list)
    def build_image(self, repo, version, uid, artifact=''):
        stub = self._get_stub()
        opts = pb.BuildImageOptions(repo=repo, version=version, uid=uid, artifact=artifact)

        for m in stub.BuildImage(opts, _STREAM_TIMEOUT):
            yield BuildImageMessage(m)

    @handle_rpc_exception(default=list)
    def create_container(self, specs, appname, image, podname, nodename, entrypoint,
                         cpu_quota, memory, count, networks, env, raw):
        stub = self._get_stub()
        opts = pb.DeployOptions(specs=specs,
                                appname=appname,
                                image=image,
                                podname=podname,
                                nodename=nodename,
                                entrypoint=entrypoint,
                                cpu_quota=cpu_quota,
                                count=count,
                                memory=memory,
                                networks=networks,
                                env=env,
                                raw=raw)

        for m in stub.CreateContainer(opts, _STREAM_TIMEOUT):
            yield CreateContainerMessage(m)

    @handle_rpc_exception(default=list)
    def remove_container(self, ids):
        stub = self._get_stub()
        ids = pb.ContainerIDs(ids=[pb.ContainerID(id=i) for i in ids])

        for m in stub.RemoveContainer(ids, _STREAM_TIMEOUT):
            yield RemoveContainerMessage(m)

    @handle_rpc_exception(default=list)
    def upgrade_container(self, ids, image):
        stub = self._get_stub()
        opts = pb.UpgradeOptions(ids=[pb.ContainerID(id=i) for i in ids], image=image)

        for m in stub.UpgradeContainer(opts, _STREAM_TIMEOUT):
            yield UpgradeContainerMessage(m)

    @handle_rpc_exception(default=list)
    def get_containers(self, ids):
        stub = self._get_stub()
        ids = pb.ContainerIDs(ids=[pb.ContainerID(id=i) for i in ids])

        cs = stub.GetContainers(ids, _UNARY_TIMEOUT)
        return [c for c in cs.containers]

    @handle_rpc_exception(default=None)
    def get_container(self, id):
        stub = self._get_stub()
        id = pb.ContainerID(id=id)
        return stub.GetContainer(id, _UNARY_TIMEOUT)
