import pytest

from .prepare import core_online, default_appname, default_sha
from citadel.models.app import Release
from citadel.tasks import build_image


pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_build_image(test_db, client):
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    release.update_image('shit')
    assert release.image == 'shit'

    image_tag = build_image(default_appname, default_sha)
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    assert '{}:{}'.format(default_appname, default_sha) in release.image

