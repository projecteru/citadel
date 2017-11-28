# -*- coding: utf-8 -*-
import pytest
from marshmallow import ValidationError

from .prepare import make_specs, default_appname, default_entrypoints, default_port


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
