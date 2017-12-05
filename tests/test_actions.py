import pytest

from .prepare import core_online, make_specs, default_appname, default_sha, default_network_name, default_podname, default_cpu_quota, default_memory
from citadel.config import BUILD_ZONE
from citadel.rpc import core_pb2 as pb
from citadel.rpc.client import get_core


pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_workflow():
    '''
    test core grpc here, no flask and celery stuff involved
    build, create, remove, and check if everything works
    '''
    specs = make_specs()
    appname = default_appname
    builds_map = {stage_name: pb.Build(**build) for stage_name, build in specs.builds.items()}
    core_builds = pb.Builds(stages=specs.stages, builds=builds_map)
    opts = pb.BuildImageOptions(name=appname,
                                user=appname,
                                uid=12345,
                                tag=default_sha,
                                builds=core_builds)
    core = get_core(BUILD_ZONE)
    build_image_messages = list(core.build_image(opts))
    image_tag = ''
    for m in build_image_messages:
        assert not m.error

    image_tag = m.progress
    assert '{}:{}'.format(default_appname, default_sha) in image_tag

    # now create container
    entrypoint_opt = pb.EntrypointOptions(name='web',
                                          command='python -m http.server',
                                          dir='/home/{}'.format(default_appname))
    networks = {default_network_name: ''}
    deploy_options = pb.DeployOptions(name=default_appname,
                                      entrypoint=entrypoint_opt,
                                      podname=default_podname,
                                      image=image_tag,
                                      cpu_quota=default_cpu_quota,
                                      memory=default_memory,
                                      count=1,
                                      networks=networks)
    deploy_messages = list(core.create_container(deploy_options))
    assert len(deploy_messages) == 1
    deploy_message = deploy_messages[0]
    assert not deploy_message.error
    assert deploy_message.memory == default_memory
    assert deploy_message.podname == default_podname
    network = deploy_message.publish
    assert len(network) == 1
    network_name, ip = network.popitem()
    assert network_name == default_network_name

    # clean this up
    container_info = deploy_messages[0]
    container_id = container_info.id
    remove_container_messages = list(core.remove_container([container_id]))
    assert len(remove_container_messages) == 1
    remove_container_message = remove_container_messages[0]
    assert remove_container_message.success is True
