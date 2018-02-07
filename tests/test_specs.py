# -*- coding: utf-8 -*-
import pytest
from marshmallow import ValidationError

from .prepare import make_specs, default_appname, default_entrypoints, default_ports


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
    assert port.port == int(default_ports[0])
    assert specs.entrypoints['web'].working_dir == '/home/{}'.format(default_appname)
    assert specs.entrypoints['test-working-dir'].working_dir == '/tmp'


def test_build():
    default_base = 'bar'
    builds = {
        'first': {
            'commands': ['echo whatever'],
        },
        'final': {
            'base': 'foo',
            'commands': ['echo whatever'],
        },
    }
    specs = make_specs(base=default_base, stages=list(builds.keys()), builds=builds)
    assert specs.builds['first']['base'] == default_base
    assert specs.builds['final']['base'] == 'foo'

    with pytest.raises(ValidationError) as exc:
        make_specs(base=None, stages=list(builds.keys()), builds=builds)

    assert 'either use a global base image as default build base, or specify base in each build stage' in str(exc)

    with pytest.raises(ValidationError) as exc:
        make_specs(stages=['wrong-stage-name'])

    assert 'stages inconsistent with' in str(exc)

    with pytest.raises(ValidationError) as exc:
        make_specs(container_user='should-not-be-here')

    assert 'cannot specify container_user because this release is not raw' in str(exc)


def test_healthcheck():
    entrypoints = {
        'web-default-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
        },
        'web-http-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
            'healthcheck_url': '/healthcheck',
            'healthcheck_http_port': 8808,
            'healthcheck_expected_code': 200,
        },
    }
    specs = make_specs(entrypoints=entrypoints)
    web_default_healthcheck = specs.entrypoints['web-default-healthcheck']
    assert web_default_healthcheck.healthcheck_tcp_ports == default_ports
    assert not web_default_healthcheck.healthcheck_url

    web_http_healthcheck = specs.entrypoints['web-http-healthcheck']
    assert web_http_healthcheck.healthcheck_http_port == 8808
    assert web_http_healthcheck.healthcheck_expected_code == 200

    # if use http health check, must define all three variables
    bad_entrypoints = {
        'web-http-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
            'healthcheck_url': '/healthcheck',
            # 'healthcheck_http_port': 8808,
            'healthcheck_expected_code': 200,
        },
    }
    with pytest.raises(ValidationError):
        make_specs(entrypoints=bad_entrypoints)

    specs = make_specs(erection_timeout=0)
    assert specs.erection_timeout == 0
