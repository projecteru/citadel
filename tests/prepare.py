# -*- coding: utf-8 -*-
import random
import string
import yaml
from humanfriendly import parse_size
from telnetlib import Telnet

from citadel.config import ZONE_CONFIG
from citadel.models.specs import Specs


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
default_ports = ['8000']
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
        'working_dir': '/tmp',
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

# test core config
default_network_name = 'etest'
default_podname = 'eru'
default_cpu_quota = 0.2
default_memory = parse_size('128MB', binary=True)


def make_specs_text(appname=default_appname,
                    entrypoints=default_entrypoints,
                    stages=list(default_builds.keys()),
                    container_user=None,
                    builds=default_builds,
                    volumes=['/tmp:/home/{}/tmp'.format(default_appname)],
                    base='hub.ricebook.net',
                    subscribers='#platform',
                    permitted_users=['liuyifu'],
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
               base='hub.ricebook.net',
               subscribers='#platform',
               permitted_users=['liuyifu'],
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
