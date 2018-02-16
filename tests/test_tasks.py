# -*- coding: utf-8 -*-

import json
import pytest
import requests

from .prepare import fake_sha, core_online, default_appname, default_sha, default_ports, default_podname, default_cpu_quota, default_memory, default_combo_name, artifact_filename, artifact_content, default_env, default_entrypoints, default_extra_args, make_specs_text
from citadel.config import DEFAULT_ZONE, FAKE_USER
from citadel.ext import get_etcd
from citadel.models.app import App, Release
from citadel.models.container import Container
from citadel.models.oplog import OPLog, OPType
from citadel.rpc.client import get_core
from citadel.tasks import create_container, remove_container, renew_container


pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_create_container(watch_etcd, request, test_app_image):
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    release.update_image(test_app_image)
    combo = release.app.get_combo(default_combo_name)
    combo.update(extra_args=default_extra_args)

    create_container_message = create_container(
        DEFAULT_ZONE,
        FAKE_USER['id'],
        default_appname,
        default_sha,
        default_combo_name,
    )[0]
    assert not create_container_message.error
    container_id = create_container_message.id

    def cleanup():
        remove_message = remove_container(container_id)[0]
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
    assert deploy_info['Extend']['healthcheck_tcp'] == ''
    assert deploy_info['Extend']['healthcheck_http'] == str(default_ports[0])
    assert deploy_info['Extend']['healthcheck_url'] == '/{}'.format(artifact_filename)
    assert int(deploy_info['Extend']['healthcheck_code']) == 200
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


def test_upgrade_container(watch_etcd, request, test_app_image):
    '''
    * upgrade old_container to container using smooth upgrade
    * then upgrade container to new_container using non-smooth upgrade (erection_timeout == 0)
    '''
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    release.update_image(test_app_image)

    create_container_message = create_container(
        DEFAULT_ZONE,
        FAKE_USER['id'],
        default_appname,
        default_sha,
        default_combo_name,
    )[0]
    assert not create_container_message.error
    old_container_id = create_container_message.id

    op_logs = OPLog.get_all()
    assert len(op_logs) == 1
    assert op_logs[0].action == OPType.CREATE_CONTAINER
    assert op_logs[0].container_id == old_container_id
    op_logs[0].delete()

    def fake_release(port=None, erection_timeout=120):
        '''
        start new container using current specs might cause port conflict if
        using host network mode, must modify port before renew container
        '''
        sha = fake_sha(40)
        if port:
            entrypoints = {
                'web': {
                    'cmd': 'python -m http.server --bind 0.0.0.0 {}'.format(port),
                    'ports': [str(port)],
                    'healthcheck': {
                        'http_url': '/{}'.format(artifact_filename),
                        'http_port': int(port),
                        'http_code': 200,
                    },
                }
            }
        else:
            entrypoints = default_entrypoints

        app = App.get_or_create(default_appname)
        r = Release.create(app, sha, make_specs_text(entrypoints=entrypoints,
                                                     erection_timeout=erection_timeout))
        r.update_image(test_app_image)
        return sha

    new_port = 8822
    sha = fake_release(new_port)
    _, create_container_message = renew_container(old_container_id, sha)
    assert not Container.get_by_container_id(old_container_id)
    container_id = create_container_message.id
    container = Container.get_by_container_id(container_id)

    assert container.is_healthy()
    _, address = container.publish.popitem()
    ip = address.split(':', 1)[0]
    artifact_url = 'http://{}:{}/{}'.format(ip, new_port, artifact_filename)
    artifact_response = requests.get(artifact_url)
    assert artifact_content in artifact_response.text

    op_logs = OPLog.get_all()
    assert len(op_logs) == 2
    assert op_logs[0].action == OPType.REMOVE_CONTAINER
    assert op_logs[0].container_id == old_container_id
    assert op_logs[1].action == OPType.CREATE_CONTAINER
    assert op_logs[1].container_id == container_id
    for op in op_logs:
        op.delete()

    new_port = 8823
    sha = fake_release(new_port, erection_timeout=0)
    _, create_container_message = renew_container(container_id, sha)
    new_container_id = create_container_message.id

    def cleanup():
        remove_message = remove_container(new_container_id)[0]
        assert remove_message.success

    request.addfinalizer(cleanup)

    assert not Container.get_by_container_id(container_id)
    new_container = Container.get_by_container_id(new_container_id)
    assert new_container.wait_for_erection(timeout=30)
    _, address = new_container.publish.popitem()
    ip = address.split(':', 1)[0]
    artifact_url = 'http://{}:{}/{}'.format(ip, new_port, artifact_filename)
    artifact_response = requests.get(artifact_url)
    assert artifact_content in artifact_response.text

    op_logs = OPLog.get_all()
    assert len(op_logs) == 2
    assert op_logs[0].action == OPType.CREATE_CONTAINER
    assert op_logs[0].container_id == new_container_id
    assert op_logs[1].action == OPType.REMOVE_CONTAINER
    assert op_logs[1].container_id == container_id
