# -*- coding: utf-8 -*-
from marshmallow import ValidationError
from humanfriendly import parse_size
from marshmallow import fields
from numbers import Number

from citadel.models.base import StrictSchema


def validate_sha(s):
    if len(s) < 7:
        raise ValidationError('sha must be longer than 7')


class RegisterSchema(StrictSchema):
    appname = fields.Str(required=True)
    sha = fields.Str(required=True, validate=validate_sha)
    git = fields.Str(required=True)
    specs_text = fields.Str(required=True)
    branch = fields.Str()
    git_tag = fields.Str()
    commit_message = fields.Str()
    author = fields.Str()


def parse_memory(s):
    if isinstance(s, Number):
        return int(s)
    return parse_size(s, binary=True)


class ComboSchema(StrictSchema):
    name = fields.Str(required=True)
    entrypoint_name = fields.Str(required=True)
    podname = fields.Str(required=True)
    nodename = fields.Str()
    networks = fields.List(fields.Str(), required=True)
    cpu_quota = fields.Float(required=True)
    memory = fields.Function(deserialize=parse_memory, required=True)
    count = fields.Int(missing=1)
    envname = fields.Str()


class DeploySchema(StrictSchema):
    appname = fields.Str(required=True)
    sha = fields.Str(required=True, validate=validate_sha)
    combo_name = fields.Str(required=True)
    podname = fields.Str()
    nodename = fields.Str()
    extra_args = fields.Str()
    cpu_quota = fields.Float()
    memory = fields.Function(deserialize=parse_memory)
    count = fields.Int()
    debug = fields.Bool()


class BuildArgsSchema(StrictSchema):
    appname = fields.Str(required=True)
    sha = fields.Str(required=True, validate=validate_sha)
