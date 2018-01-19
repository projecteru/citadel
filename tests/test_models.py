# -*- coding: utf-8 -*-
import pytest
from marshmallow import ValidationError

from .prepare import make_specs, default_appname, default_entrypoints, default_ports
from citadel.models.app import EnvSet


def test_env_set():
    env_set = EnvSet(FOO='23=', BAR='shit\\')
    assert env_set.to_env_vars() == ['FOO=23=', 'BAR=shit\\']
    with pytest.raises(ValueError):
        EnvSet(ERU_POD='whatever')
