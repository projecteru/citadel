# -*- coding: utf-8 -*-
import pytest
import yaml
from marshmallow import ValidationError

from citadel.models.specs import Specs


default_entrypoints = {
    'web': {
        'cmd': './run.py',
        'ports': ['8888/tcp'],
    },
}
default_combos = {
    'prod-web': {
        'cpu': 1.0,
        'memory': '512MB',
        'podname': 'develop',
        'entrypoint': 'web',
        'networks': ['release'],
    }
}


def make_specs(appname='test-ci',
               entrypoints=default_entrypoints,
               build=['echo hello'],
               volumes=[],
               base='hub.ricebook.net',
               subscribers='#platform',
               permitted_users=['liuyifu'],
               combos=default_combos,
               crontab=[],
               **kwargs):
    specs_dict = locals()
    kwargs = specs_dict.pop('kwargs')
    for k, v in kwargs.items():
        specs_dict[k] = v

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
    assert port.port == 8888
