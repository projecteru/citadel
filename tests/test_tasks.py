import json
import pytest
import requests

from .prepare import core_online, default_appname, default_sha, default_ports, default_podname, default_cpu_quota, default_memory, default_combo_name, artifact_filename, artifact_content, default_env, default_entrypoints, default_extra_args
from citadel.config import DEFAULT_ZONE
from citadel.ext import get_etcd
from citadel.models.app import Release
from citadel.models.container import Container
from citadel.rpc.client import get_core
from citadel.tasks import build_image, create_container, remove_container


pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_workflow(watch_etcd, request):
    """
    test celery tasks, all called synchronously
    build, create, upgrade, remove, and check if everything works
    """
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    release.update_image('shit')
    build_image(default_appname, default_sha)
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    image_tag = release.image
    assert '{}:{}'.format(default_appname, default_sha) in image_tag

    deploy_messages = list(create_container(zone=DEFAULT_ZONE,
                                            appname=default_appname,
                                            sha=default_sha,
                                            combo_name=default_combo_name))
    assert len(deploy_messages) == 1
    container_info = deploy_messages[0]
    assert not container_info.error
    container_id = container_info.id

    def cleanup():
        remove_messages = remove_container(container_id)
        assert len(remove_messages) == 1
        remove_message = remove_messages[0]
        assert remove_message.success

    request.addfinalizer(cleanup)

    container = Container.get_by_container_id(container_id)
    # agent 肯定还没探测到, 所以 deploy_info 应该是默认值
    assert container.deploy_info == {}
    assert container.combo_name == default_combo_name
    assert container.podname == default_podname
    assert container.memory == default_memory
    assert float(container.cpu_quota) == default_cpu_quota

    # check etcd data at /eru-core/deploy/test-app/web
    assert container.wait_for_erection()
    etcd = get_etcd(DEFAULT_ZONE)
    deploy_info = json.loads(etcd.read(container.core_deploy_key).value)

    # check watch_etcd process is actually working
    assert container.deploy_info == deploy_info

    assert deploy_info['Healthy'] is True
    assert deploy_info['Extend']['healthcheck_tcp'] == ','.join(default_ports)
    assert deploy_info['Extend']['healthcheck_http'] == str(default_ports[0])
    assert deploy_info['Extend']['healthcheck_url'] == '/{}'.format(artifact_filename)
    publish = deploy_info['Publish']
    assert len(publish) == 1
    network_name, address = publish.popitem()
    ip = address.split(':', 1)[0]

    artifact_url = 'http://{}:{}/{}'.format(ip, default_ports[0], artifact_filename)
    artifact_response = requests.get(artifact_url)
    assert artifact_content in artifact_response.text

    core = get_core(DEFAULT_ZONE)
    container_info = json.loads(core.get_container(container_id).info)
    assert '/tmp:/home/test-app/tmp:rw' in container_info['HostConfig']['Binds']

    # check environment variables from combo is actually injected into the
    # container
    left_env_vars = set(default_env.to_env_vars())
    right_env_vars = set(container_info['Config']['Env'])
    assert left_env_vars.intersection(right_env_vars) == left_env_vars

    # verify extra_args has been correctly appended
    left_command = '{} {}'.format(default_entrypoints['web']['cmd'], default_extra_args)
    right_command = ' '.join(container_info['Config']['Cmd'])
    assert left_command == right_command
