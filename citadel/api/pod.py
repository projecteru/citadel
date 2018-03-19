# -*- coding: utf-8 -*-
"""Pod / Node management API"""

from citadel.libs.view import create_api_blueprint
from citadel.models.container import Container
from citadel.rpc.client import get_core
from flask import g, abort


bp = create_api_blueprint('pod', __name__, 'pod')


def _get_pod(name):
    pod = get_core(g.zone).get_pod(name)
    if not pod:
        abort(404, 'pod `%s` not found' % name)

    return pod


@bp.route('/')
def get_all_pods():
    """List all pods

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "name": "eru",
                "desc": "eru test pod",
                "__class__": "Pod"
            }
        ]
    """
    return get_core(g.zone).list_pods()


@bp.route('/<name>')
def get_pod(name):
    """Get a single pod by name

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "name": "eru",
            "desc": "eru test pod",
            "__class__": "Pod"
        }
    """
    return _get_pod(name)


@bp.route('/<name>/nodes')
def get_pod_nodes(name):
    """List nodes under a pod

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "name": "c1-eru-2.ricebook.link",
                "endpoint": "tcp://xxx.xxx.xxx.xxx:2376",
                "podname": "eru",
                "cpu": {"0": 75},
                "memory": 855085056,
                "info": "{\\"ID\\":\\"UUWL:QZS7:MPQY:KMYY:T5Q4:GCBY:JBRA:Q55K:NUKW:O2N2:4BEX:UTFK\\",\\"Containers\\":7,\\"ContainersRunning\\":6,\\"ContainersPaused\\":0,\\"ContainersStopped\\":1,\\"Images\\":9,\\"Driver\\":\\"overlay\\",\\"DriverStatus\\":[[\\"Backing Filesystem\\",\\"xfs\\"],[\\"Supports d_type\\",\\"false\\"]],\\"SystemStatus\\":null,\\"Plugins\\":{\\"Volume\\":[\\"local\\"],\\"Network\\":[\\"bridge\\",\\"host\\",\\"macvlan\\",\\"null\\",\\"overlay\\"],\\"Authorization\\":null},\\"MemoryLimit\\":true,\\"SwapLimit\\":true,\\"KernelMemory\\":true,\\"CpuCfsPeriod\\":true,\\"CpuCfsQuota\\":true,\\"CPUShares\\":true,\\"CPUSet\\":true,\\"IPv4Forwarding\\":true,\\"BridgeNfIptables\\":true,\\"BridgeNfIp6tables\\":true,\\"Debug\\":false,\\"NFd\\":57,\\"OomKillDisable\\":true,\\"NGoroutines\\":72,\\"SystemTime\\":\\"2018-03-20T16:10:51.806831123+08:00\\",\\"LoggingDriver\\":\\"json-file\\",\\"CgroupDriver\\":\\"cgroupfs\\",\\"NEventsListener\\":1,\\"KernelVersion\\":\\"3.10.0-693.5.2.el7.x86_64\\",\\"OperatingSystem\\":\\"CentOS Linux 7 (Core)\\",\\"OSType\\":\\"linux\\",\\"Architecture\\":\\"x86_64\\",\\"IndexServerAddress\\":\\"https://index.docker.io/v1/\\",\\"RegistryConfig\\":{\\"InsecureRegistryCIDRs\\":[\\"127.0.0.0/8\\"],\\"IndexConfigs\\":{\\"docker.io\\":{\\"Name\\":\\"docker.io\\",\\"Mirrors\\":[\\"https://registry.docker-cn.com/\\"],\\"Secure\\":true,\\"Official\\":true}},\\"Mirrors\\":[\\"https://registry.docker-cn.com/\\"]},\\"NCPU\\":1,\\"MemTotal\\":1928826880,\\"DockerRootDir\\":\\"/var/lib/docker\\",\\"HttpProxy\\":\\"\\",\\"HttpsProxy\\":\\"\\",\\"NoProxy\\":\\"\\",\\"Name\\":\\"c1-eru-2.ricebook.link\\",\\"Labels\\":[],\\"ExperimentalBuild\\":false,\\"ServerVersion\\":\\"17.12.1-ce\\",\\"ClusterStore\\":\\"etcd://127.0.0.1:2379\\",\\"ClusterAdvertise\\":\\"\\",\\"Runtimes\\":{\\"runc\\":{\\"path\\":\\"docker-runc\\"}},\\"DefaultRuntime\\":\\"runc\\",\\"Swarm\\":{\\"NodeID\\":\\"\\",\\"NodeAddr\\":\\"\\",\\"LocalNodeState\\":\\"inactive\\",\\"ControlAvailable\\":false,\\"Error\\":\\"\\",\\"RemoteManagers\\":null},\\"LiveRestoreEnabled\\":false,\\"Isolation\\":\\"\\",\\"InitBinary\\":\\"docker-init\\",\\"ContainerdCommit\\":{\\"ID\\":\\"9b55aab90508bd389d7654c4baf173a981477d55\\",\\"Expected\\":\\"9b55aab90508bd389d7654c4baf173a981477d55\\"},\\"RuncCommit\\":{\\"ID\\":\\"9f9c96235cc97674e935002fc3d78361b696a69e\\",\\"Expected\\":\\"9f9c96235cc97674e935002fc3d78361b696a69e\\"},\\"InitCommit\\":{\\"ID\\":\\"949e6fa\\",\\"Expected\\":\\"949e6fa\\"},\\"SecurityOptions\\":[\\"name=seccomp,profile=default\\"]}",
            "available": true,
            "labels": {},
            "__class__": "Node"
            }
        ]
    """
    pod = _get_pod(name)
    return get_core(g.zone).get_pod_nodes(pod.name)


@bp.route('/<name>/containers')
def get_pod_containers(name):
    pod = _get_pod(name)
    return Container.get_by(zone=g.zone, podname=pod.name)


@bp.route('/<name>/networks')
def list_networks(name):
    """List networks under a pod

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {"name": "host", "subnets": [], "__class__": "Network"},
            {"name": "bridge", "subnets": ["172.17.0.0/16"], "__class__": "Network"}
        ]
    """
    pod = _get_pod(name)
    return get_core(g.zone).list_networks(pod.name)
