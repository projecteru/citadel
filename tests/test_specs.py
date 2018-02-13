# -*- coding: utf-8 -*-
import pytest
from marshmallow import ValidationError

from citadel.models.app import Release
from .prepare import make_specs, default_appname, default_entrypoints, default_ports, default_sha, default_combo_name, healthcheck_http_url


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


def test_healthcheck(test_db):
    entrypoints = {
        'default-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
        },
        'http-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
            'healthcheck': {
                'http_url': healthcheck_http_url,
                'http_port': default_ports[0],
                'http_code': 200,
            }
        },
        'http-partial-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
            'healthcheck': {
                'http_url': healthcheck_http_url,
                'http_port': default_ports[0],
            }
        },
    }
    specs = make_specs(entrypoints=entrypoints)
    default_healthcheck = specs.entrypoints['default-healthcheck'].healthcheck
    assert default_healthcheck.tcp_ports == default_ports
    assert not default_healthcheck.http_url
    assert not default_healthcheck.http_port
    assert not default_healthcheck.http_code

    http_healthcheck = specs.entrypoints['http-healthcheck'].healthcheck
    assert http_healthcheck.http_port == int(default_ports[0])
    assert http_healthcheck.http_code == 200

    http_partial_healthcheck = specs.entrypoints['http-partial-healthcheck'].healthcheck
    assert http_partial_healthcheck.http_code == 200

    # if use http health check, must define all three variables
    bad_entrypoints = {
        'http-healthcheck': {
            'cmd': 'python -m http.server',
            'ports': default_ports,
            'healthcheck': {
                # missing http_port and http_code
                'http_url': '/healthcheck',
            }
        },
    }
    with pytest.raises(ValidationError) as e:
        make_specs(entrypoints=bad_entrypoints)

    assert 'If you plan to use HTTP health check, you must define (at least) http_port, http_url' in str(e)

    specs = make_specs(erection_timeout=0)
    assert specs.erection_timeout == 0

    # see if grpc messages are correctly rendered
    release = Release.get_by_app_and_sha(default_appname, default_sha)
    deploy_opt = release.make_core_deploy_options(default_combo_name)
    healthcheck_opt = deploy_opt.entrypoint.healthcheck
    assert healthcheck_opt.tcp_ports == []
    assert healthcheck_opt.http_port == str(default_ports[0])
    assert healthcheck_opt.url == healthcheck_http_url
    assert healthcheck_opt.code == 200
