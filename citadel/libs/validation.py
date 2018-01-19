# -*- coding: utf-8 -*-
from humanfriendly import parse_size
from marshmallow import ValidationError, fields
from numbers import Number

from citadel.models.base import StrictSchema


def validate_sha(s):
    if len(s) < 7:
        raise ValidationError('sha must be longer than 7')


def validate_full_contianer_id(s):
    if len(s) < 64:
        raise ValidationError('Container ID must be of length 64')


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
    podname = fields.Str(required=True)
    nodename = fields.Str()
    extra_args = fields.Str()
    cpu_quota = fields.Float(required=True)
    memory = fields.Function(deserialize=parse_memory, required=True)
    count = fields.Int(missing=1)
    debug = fields.Bool(missing=False)


class DeployELBSchema(StrictSchema):
    name = fields.Str(required=True)
    sha = fields.Str(required=True, validate=validate_sha)
    combo_name = fields.Str(required=True)
    nodename = fields.Str()


class BuildArgsSchema(StrictSchema):
    appname = fields.Str(required=True)
    sha = fields.Str(required=True, validate=validate_sha)


class RemoveContainerSchema(StrictSchema):
    container_ids = fields.List(fields.Str(required=True, validate=validate_full_contianer_id), required=True)


class CreateELBRulesSchema(StrictSchema):
    appname = fields.Str(required=True)
    podname = fields.Str(required=True)
    entrypoint_name = fields.Str(required=True)
    domain = fields.Str(required=True)
    arguments = fields.Dict(default={})


deploy_schema = DeploySchema()
deploy_elb_schema = DeployELBSchema()
build_args_schema = BuildArgsSchema()
remove_container_schema = RemoveContainerSchema()
