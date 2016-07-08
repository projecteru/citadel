# coding: utf-8

from functools import partial
from grpc.beta import implementations
from grpc.framework.interfaces.face.face import AbortionError

import citadel.rpc.core_pb2 as pb
from citadel.libs.utils import handle_exception
from citadel.rpc.exceptions import NoStubError
from citadel.rpc.core import Pod, Node, BuildImageMessage, CreateContainerMessage, UpgradeContainerMessage


handle_rpc_exception = partial(handle_exception, (NoStubError, AbortionError))


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
        r = stub.ListPods(pb.Empty(), 5)
        return [Pod(p) for p in r.pods]

    @handle_rpc_exception(default=None)
    def create_pod(self, name, desc):
        stub = self._get_stub()
        opts = pb.AddPodOptions(name=name, desc=desc)
        p = stub.AddPod(opts, 5)
        return p and Pod(p)

    @handle_rpc_exception(default=None)
    def get_pod(self, name):
        stub = self._get_stub()
        opts = pb.GetPodOptions(name=name)
        p = stub.GetPod(opts, 5)
        return p and Pod(p)

    @handle_rpc_exception(default=list)
    def get_pod_nodes(self, name):
        stub = self._get_stub()
        opts = pb.ListNodesOptions(podname=name)
        r = stub.ListPodNodes(opts, 5)
        return [Node(n) for n in r.nodes]

    @handle_rpc_exception(default=None)
    def get_node(self, podname, nodename):
        stub = self._get_stub()
        opts = pb.GetNodeOptions(podname=podname, nodename=nodename)
        n = stub.GetNode(opts, 5)
        return n and Node(n)

    @handle_rpc_exception(default=None)
    def add_node(self, nodename, endpoint, podname, public):
        stub = self._get_stub()
        opts = pb.AddNodeOptions(nodename=nodename,
                                 endpoint=endpoint,
                                 podname=podname,
                                 public=public)
    
        n = stub.AddNode(opts, 5)
        return n and Node(n)

    @handle_rpc_exception(default=list)
    def build_image(self, repo, version, uid, artifact=''):
        stub = self._get_stub()
        opts = pb.BuildImageOptions(repo=repo, version=version, uid=uid, artifact=artifact)
    
        for m in stub.BuildImage(opts, 3600):
            yield BuildImageMessage(m)

    @handle_rpc_exception(default=list)
    def create_container(self, specs, appname, image, podname, entrypoint,
            cpu_quota, count, networks, env):
        stub = self._get_stub()
        opts = pb.DeployOptions(specs=specs,
                                appname=appname,
                                image=image,
                                podname=podname,
                                entrypoint=entrypoint,
                                cpu_quota=cpu_quota,
                                count=count,
                                networks=networks,
                                env=env)
    
        for m in stub.CreateContainer(opts, 3600):
            yield CreateContainerMessage(m)

    @handle_rpc_exception(default=list)
    def remove_container(self, ids):
        stub = self._get_stub()
        ids = pb.ContainerIDs(ids=[pb.ContainerID(id=i) for i in ids])
    
        for m in stub.RemoveContainer(ids, 3600):
            yield m

    @handle_rpc_exception(default=list)
    def upgrade_container(self, ids, image):
        stub = self._get_stub()
        opts = pb.UpgradeOptions(ids=[pb.ContainerID(id=i) for i in ids], image=image)
    
        for m in stub.UpgradeContainer(opts, 3600):
            yield UpgradeContainerMessage(m)

    @handle_rpc_exception(default=list)
    def get_containers(self, ids):
        stub = self._get_stub()
        ids = pb.ContainerIDs(ids=[pb.ContainerID(id=i) for i in ids])
    
        cs = stub.GetContainers(ids, 3600)
        return [c for c in cs.containers]
