# -*- coding: utf-8 -*-
import string
import random
import pytest
import yaml
from marshmallow import ValidationError

from citadel.models.specs import Specs


default_appname = 'test-app'
default_sha = '651fe0a'
default_port = ['8000']
artifact_content = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
artifact_filename = '{}-data.txt'.format(default_appname)
default_entrypoints = {
    'web': {
        'cmd': 'python -m http.server',
        'ports': default_port,
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


def test_extra_fields():
    # do not allow unknown fields
    # for example, a typo
    with pytest.raises(ValidationError):
        make_specs(typo_field='whatever')


def test_entrypoints():
    # no underscore in entrypoint_name
    bad_entrypoints = default_entrypoints.copy()
    bad_entrypoints['web_prod'] = bad_entrypoints.pop('web')
    with pytest.raises(ValidationError):
        make_specs(entrypoints=bad_entrypoints)

    # validate ports parsing
    specs = make_specs()
    port = specs.entrypoints['web'].ports[0]
    assert port.protocol == 'tcp'
    assert port.port == int(default_port[0])
    assert specs.entrypoints['web'].working_dir == '/home/{}'.format(default_appname)
    assert specs.entrypoints['test-working-dir'].working_dir == '/tmp'


def test_build():
    with pytest.raises(ValidationError):
        make_specs(stages=['wrong-stage-name'])

    with pytest.raises(ValidationError):
        make_specs(container_user='should-not-be-here')
