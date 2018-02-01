# -*- coding: utf-8 -*-
import random
import string
import yaml
from humanfriendly import parse_size
from telnetlib import Telnet

from citadel.config import ZONE_CONFIG, BUILD_ZONE
from citadel.models.specs import Specs
from citadel.models.app import EnvSet
from citadel.models.container import ContainerOverrideStatus, Container


core_online = False
try:
    for zone in ZONE_CONFIG.values():
        ip, port = zone['CORE_URL'].split(':')
        Telnet(ip, port).close()
        core_online = True
except ConnectionRefusedError:
    core_online = False


default_appname = 'test-app'
default_sha = '651fe0a'
default_ports = ['6789']
default_git = 'git@github.com:projecteru2/citadel.git'
artifact_content = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
artifact_filename = '{}-data.txt'.format(default_appname)
default_entrypoints = {
    'web': {
        'cmd': 'python -m http.server',
        'ports': default_ports,
        'healthcheck_http_port': int(default_ports[0]),
        'healthcheck_url': '/{}'.format(artifact_filename),
        'healthcheck_expected_code': 200,
    },
    'web-bad-ports': {
        'cmd': 'python -m http.server',
        'ports': ['8000', '8001'],
    },
    'test-working-dir': {
        'cmd': 'echo pass',
        'dir': '/tmp',
    },
}
default_builds = {
    'make-artifacts': {
        'base': 'python:latest',
        'commands': ['echo {} > {}'.format(artifact_content, artifact_filename)],
        'cache': {artifact_filename: '/home/{}/{}'.format(default_appname, artifact_filename)},
    },
    'pack': {
        'base': 'python:latest',
        'commands': ['mkdir -p /etc/whatever'],
    },
}
default_combo_name = 'prod'
default_env_name = 'prodenv'
default_env = EnvSet(**{'foo': 'some-env-content'})

# test core config
default_network_name = 'bridge'
default_podname = 'eru'
default_extra_args = '--bind 0.0.0.0 {}'.format(default_ports[0])
default_cpu_quota = 0.2
default_memory = parse_size('128MB', binary=True)


def make_specs_text(appname=default_appname,
                    entrypoints=default_entrypoints,
                    stages=list(default_builds.keys()),
                    container_user=None,
                    builds=default_builds,
                    volumes=['/tmp:/home/{}/tmp'.format(default_appname)],
                    base='python:latest',
                    subscribers='#platform',
                    crontab=[],
                    **kwargs):
    specs_dict = locals()
    kwargs = specs_dict.pop('kwargs')
    for k, v in kwargs.items():
        specs_dict[k] = v

    specs_dict = {k: v for k, v in specs_dict.items() if v}
    specs_string = yaml.dump(specs_dict)
    return specs_string


def make_specs(appname=default_appname,
               entrypoints=default_entrypoints,
               stages=list(default_builds.keys()),
               container_user=None,
               builds=default_builds,
               volumes=['/tmp:/home/{}/tmp'.format(default_appname)],
               base='python:latest',
               subscribers='#platform',
               crontab=[],
               **kwargs):
    specs_dict = locals()
    kwargs = specs_dict.pop('kwargs')
    for k, v in kwargs.items():
        specs_dict[k] = v

    specs_dict = {k: v for k, v in specs_dict.items() if v}
    specs_string = yaml.dump(specs_dict)
    Specs.validate(specs_string)
    return Specs.from_string(specs_string)


def fake_container(appname=default_appname, sha=default_sha, container_id=None,
                   container_name=None, entrypoint_name='web',
                   envname=default_env_name, cpu_quota=default_cpu_quota,
                   memory=default_memory, zone=BUILD_ZONE,
                   podname=default_podname, nodename='whatever',
                   override_status=ContainerOverrideStatus.NONE):
    if not sha:
        sha = ''.join(random.choices(string.hexdigits.lower(), k=40))

    if not container_id:
        container_id = ''.join(random.choices(string.hexdigits.lower(), k=64))

    if not container_name:
        container_name = ''.join(random.choices(string.hexdigits.lower(), k=16))

    Container.create(**locals())
