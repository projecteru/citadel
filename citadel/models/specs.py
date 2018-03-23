# -*- coding: utf-8 -*-

from box import Box
from crontab import CronTab
from humanfriendly import InvalidTimespan, parse_timespan, parse_size
from marshmallow import fields, validates_schema, ValidationError, post_load
from numbers import Number

from citadel.models.base import StrictSchema


def validate_port(n):
    if not 0 < n <= 65535:
        raise ValidationError('Port must be 0-65,535')


def validate_restart(s):
    if s not in {'no', 'unless-stopped', 'always', 'on-failure'}:
        raise ValidationError('Bad restart policy: {}'.format(s))


def validate_http_code(n):
    if not 100 <= n <= 599:
        raise ValidationError('HTTP code should be 100-599')


def validate_log_config(s):
    if s not in {'json-file', 'none', 'syslog'}:
        raise ValidationError('Log config should choose from json-file, none, syslog')


def validate_entrypoint_name(s):
    if '_' in s:
        raise ValidationError('Entrypoints must not contain underscore')


def validate_cpu(n):
    if n < 0:
        raise ValidationError('CPU must >=0')


def validate_elb_domain(s):
    if not len(s.split()) == 2:
        raise ValidationError('Bad ELB domain record, should be \'$ELB_NAME $DOMAIN\'')


def parse_builds(dic):
    '''
    `builds` clause within app.yaml contains None or several build stages, this
    function validates every stage within
    '''
    for stage_name, build in dic.items():
        unmarshal_result = build_schema.load(build)
        dic[stage_name] = unmarshal_result.data

    return dic


def parse_memory(s):
    return parse_size(s, binary=True) if isinstance(s, str) else s


def parse_extra_env(s):
    extra_env = {}
    if isinstance(s, str):
        parts = s.split(';')
        for p in parts:
            if not p:
                continue
            k, v = p.split('=', 1)
            extra_env[k] = v

    return extra_env


def parse_entrypoints(dic):
    for entrypoint_name, entrypoint_dic in dic.items():
        validate_entrypoint_name(entrypoint_name)
        unmarshal_result = entrypoint_schema.load(entrypoint_dic)
        dic[entrypoint_name] = unmarshal_result.data

    return dic


def better_parse_timespan(s):
    if isinstance(s, str):
        try:
            seconds = parse_timespan(s)
        except InvalidTimespan as e:
            raise ValidationError(str(e))
    elif isinstance(s, Number):
        seconds = float(s)
    else:
        raise ValidationError('erection_timeout should be int or str')
    return seconds


def parse_cron_line(s):
    try:
        cron_part = ' '.join(s.split()[:5])
        crontab = CronTab(cron_part)
        cmd = s.replace(cron_part, '').strip()
    except IndexError as e:
        raise ValidationError(str(e))
    return crontab, cmd


def parse_crontab(cron_list):
    cron_settings = [parse_cron_line(s) for s in cron_list]
    return cron_settings


class BuildSchema(StrictSchema):
    base = fields.Str()
    repo = fields.Str()
    version = fields.Str()
    working_dir = fields.Str(load_from='dir')
    commands = fields.List(fields.Str())
    envs = fields.Dict()
    args = fields.Dict()
    labels = fields.Dict()
    artifacts = fields.Dict()
    cache = fields.Dict()


build_schema = BuildSchema()


class HealthCheckSchema(StrictSchema):
    tcp_ports = fields.List(fields.Int(validate=validate_port), missing=[])
    http_port = fields.Int(validate=validate_port)
    http_url = fields.Str()
    http_code = fields.Int(validate=validate_http_code)

    @post_load
    def fix_defaults(self, data):
        if data.get('http_port') and data.get('http_url'):
            data['http_code'] = 200

    @validates_schema
    def validate_http(self, data):
        healthcheck_stuff = [data.get('http_port'),
                             data.get('http_url')]
        if any(healthcheck_stuff) and not all(healthcheck_stuff):
            raise ValidationError('If you plan to use HTTP health check, you must define (at least) http_port, http_url')


class HookSchema(StrictSchema):
    after_start = fields.List(fields.Str(), missing=[])
    before_stop = fields.List(fields.Str(), missing=[])
    force = fields.Bool()


class EntrypointSchema(StrictSchema):
    command = fields.Str(required=True, load_from='cmd')
    image = fields.Str()
    publish = fields.List(fields.Str(), missing=[], load_from='ports')
    network_mode = fields.Str()
    restart = fields.Str(validate=validate_restart)
    healthcheck = fields.Nested(HealthCheckSchema)
    privileged = fields.Bool(missing=False)
    log_config = fields.Str(validate=validate_log_config)
    working_dir = fields.Str(load_from='dir')
    hook = fields.Nested(HookSchema)
    backup_path = fields.List(fields.Str(), missing=[])

    @post_load
    def finalize(self, data):
        # if there's anything to be published to ELB, give em some free tcp
        # healthcheck, if there's no healthcheck defined at all
        publish = data.get('publish')
        if publish and not data.get('healthcheck'):
            data['healthcheck'] = {
                'tcp_ports': publish,
            }

        return data


entrypoint_schema = EntrypointSchema()


class SpecsSchema(StrictSchema):
    appname = fields.Str(required=True)
    name = fields.Str()
    entrypoints = fields.Function(deserialize=parse_entrypoints, required=True)
    dns = fields.List(fields.Str())
    hosts = fields.List(fields.Str())
    stages = fields.List(fields.Str())
    container_user = fields.Str()
    builds = fields.Function(deserialize=parse_builds, missing={})
    volumes = fields.List(fields.Str())
    base = fields.Str()
    subscribers = fields.Str(required=True)
    erection_timeout = fields.Function(deserialize=better_parse_timespan, missing=parse_timespan('2m'))
    crontab = fields.Function(deserialize=parse_crontab, missing=[])

    @post_load
    def finalize(self, data):
        """add defaults to fields, and then construct a Box"""
        if 'name' not in data:
            data['name'] = data['appname']

        default_build_base = data.get('base')
        if default_build_base:
            for build in data['builds'].values():
                if 'base' not in build:
                    build['base'] = default_build_base

        for entrypoint in data['entrypoints'].values():
            # set default working_dir to app's home
            if not entrypoint.get('working_dir'):
                entrypoint['working_dir'] = '/home/{}'.format(data['appname'])

        return Box(data, conversion_box=False, default_box=True,
                   default_box_attr=None, frozen_box=True)

    @validates_schema
    def validate_misc(self, data):
        # check raw related fields
        stages = data.get('stages')
        builds = data.get('builds')
        if set(stages) != set(builds):
            raise ValidationError('stages inconsistent with builds: {} vs {}'.format(stages, list(builds.keys())))

        raw = False if stages else True
        if not raw and data.get('container_user'):
            raise ValidationError('cannot specify container_user because this release is not raw')
        if raw and not data.get('base'):
            raise ValidationError('this is a raw release, must specify base')

        if not data.get('base'):
            for build in builds.values():
                if not build.get('base'):
                    raise ValidationError('either use a global base image as default build base, or specify base in each build stage')


specs_schema = SpecsSchema()
