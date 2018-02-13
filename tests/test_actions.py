# -*- coding: utf-8 -*-

import pytest

from .prepare import core_online, default_appname, default_network_name, default_podname, default_cpu_quota, default_memory
from citadel.config import BUILD_ZONE
from citadel.rpc import core_pb2 as pb
from citadel.rpc.client import get_core


pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_workflow(request, test_app_image):
    '''
    test core grpc here, no flask and celery stuff involved
    build, create, remove, and check if everything works
    '''
    core = get_core(BUILD_ZONE)
    # now create container
    entrypoint_opt = pb.EntrypointOptions(name='web',
                                          command='python -m http.server',
                                          dir='/home/{}'.format(default_appname))
    networks = {default_network_name: ''}
    deploy_opt = pb.DeployOptions(name=default_appname,
                                  entrypoint=entrypoint_opt,
                                  podname=default_podname,
                                  image=test_app_image,
                                  cpu_quota=default_cpu_quota,
                                  memory=default_memory,
                                  count=1,
                                  networks=networks)
    deploy_messages = list(core.create_container(deploy_opt))

    container_info = deploy_messages[0]
    container_id = container_info.id

    def cleanup():
        remove_container_messages = list(core.remove_container([container_id]))
        remove_container_message = remove_container_messages[0]
        assert remove_container_message.success

    request.addfinalizer(cleanup)

    assert len(deploy_messages) == 1
    deploy_message = deploy_messages[0]
    assert not deploy_message.error
    assert deploy_message.memory == default_memory
    assert deploy_message.podname == default_podname
    network = deploy_message.publish
    assert len(network) == 1
    network_name, ip = network.popitem()
    assert network_name == default_network_name
