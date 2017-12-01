import pytest

from .prepare import (core_online, default_appname, default_sha,
                      default_podname, default_cpu_quota, default_memory,
                      default_combo_name)
from citadel.config import DEFAULT_ZONE
from citadel.models.app import Release
from citadel.models.container import Container
from citadel.tasks import build_image, create_container, remove_container


pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_workflow(test_db):
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
                                            combo_name=default_combo_name,
                                            podname=default_podname,
                                            cpu_quota=default_cpu_quota,
                                            memory=default_memory, count=1))
    assert len(deploy_messages) == 1
    container_info = deploy_messages[0]
    assert not container_info['error']
    container_id =  container_info['id']
    container = Container.get_by_container_id(container_id)
    assert container.podname == default_podname
    assert container.memory == default_memory
    assert float(container.cpu_quota) == default_cpu_quota
    # TODO: check network

    remove_messages = list(remove_container(container_id))
    assert len(remove_messages) == 1
    remove_message = remove_messages[0]
    assert remove_message['success']
