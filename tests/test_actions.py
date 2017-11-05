import pytest
from telnetlib import Telnet

from .test_specs import make_specs
from citadel.config import ZONE_CONFIG, BUILD_ZONE
from citadel.rpc import get_core
from citadel.rpc import core_pb2 as pb


core_online = False
try:
    for zone in ZONE_CONFIG.values():
        ip, port = zone['CORE_URL'].split(':')
        Telnet(ip, port).close()
        core_online = True
except ConnectionRefusedError:
    core_online = False

pytestmark = pytest.mark.skipif(not core_online, reason='one or more eru-core is offline, skip core-related tests')


def test_build():
    specs = make_specs()
    appname = 'test-app'
    builds_map = {stage_name: pb.Build(**build) for stage_name, build in specs.builds.items()}
    core_builds = pb.Builds(stages=specs.stages, builds=builds_map)
    opts = pb.BuildImageOptions(name=appname,
                                user=appname,
                                uid=12345,
                                tag='651fe0a',
                                builds=core_builds)
    core = get_core(BUILD_ZONE)
    build_image_messages = list(core.build_image(opts))
    for m in build_image_messages:
        assert not m.error
