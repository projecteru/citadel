# -*- coding: utf-8 -*-

import yaml
from crontab import CronTab
from humanfriendly import InvalidTimespan, parse_timespan, parse_size
from marshmallow import fields, validates_schema, ValidationError, post_load
from numbers import Number

from citadel.libs.jsonutils import Jsonized
from citadel.libs.utils import memoize
from citadel.models.base import StrictSchema


def validate_protocol(s):
    if s not in {'http', 'tcp'}:
        raise ValidationError('ELB port should talk tcp or http')


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
        errors = unmarshal_result.errors
        if errors:
            raise ValidationError(str(errors))
        dic[stage_name] = unmarshal_result.data

    return dic


def parse_single_port(port_string):
    if isinstance(port_string, Number):
        data = {'port': str(port_string), 'protocol': 'tcp'}
    else:
        parts = port_string.split('/')
        try:
            port = int(parts[0])
        except ValueError:
            raise ValidationError('Bad port: {}'.format(port_string))
        if len(parts) == 2:
            protocol = parts[1]
        elif len(parts) == 1:
            protocol = 'tcp'
        else:
            raise ValidationError('Multiple slashes in port: {}'.format(port_string))
        data = {'port': port, 'protocol': protocol}

    unmarshal_result = PortSchema().load(data)
    errors = unmarshal_result.errors
    if errors:
        raise ValidationError(str(errors))
    return unmarshal_result.data


def parse_port_list(port_list):
    return [parse_single_port(s) for s in port_list]


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
        errors = unmarshal_result.errors
        if errors:
            raise ValidationError(str(errors))
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
        l = s.split()
        cron_part = ' '.join(l[:5])
        crontab = CronTab(cron_part)
        cmd = s.replace(cron_part, '').strip()
    except IndexError as e:
        raise ValidationError(str(e))
    return crontab, cmd


def parse_crontab(cron_list):
    cron_settings = [parse_cron_line(s) for s in cron_list]
    return cron_settings


class PortSchema(StrictSchema):
    protocol = fields.Str(validate=validate_protocol, missing='tcp')
    port = fields.Int(validate=validate_port, required=True)


class Port(Jsonized):
    def __init__(self, protocol=None, port=None, _raw=None):
        self.protocol = protocol
        self.port = port
        self._raw = _raw


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
    http_port = fields.Int(validate=validate_port, missing='')
    http_url = fields.Str(missing='')
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


class HealthCheck(Jsonized):
    def __init__(self, tcp_ports=None, http_port=None, http_url=None, http_code=None, _raw=None):
        self.tcp_ports = tcp_ports
        self.http_port = http_port
        self.http_url = http_url
        self.http_code = http_code
        self._raw = _raw


class EntrypointSchema(StrictSchema):
    cmd = fields.Str(attribute='command', required=True)
    image = fields.Str()
    ports = fields.Function(deserialize=parse_port_list, missing=[])
    network_mode = fields.Str()
    restart = fields.Str(validate=validate_restart)
    healthcheck = fields.Nested(HealthCheckSchema)
    privileged = fields.Bool(missing=False)
    log_config = fields.Str(validate=validate_log_config)
    working_dir = fields.Str(load_from='dir')
    after_start = fields.Str()
    before_stop = fields.Str()
    backup_path = fields.List(fields.Str(), missing=[])


class Entrypoint(Jsonized):
    def __init__(self, command=None, image=None, ports=None, network_mode=None,
                 restart=None, healthcheck={}, hosts=None, privileged=None,
                 log_config=None, working_dir=None, after_start=None,
                 before_stop=None, backup_path=None, _raw=None):
        self.command = command
        self.image = image
        self.ports = [Port(_raw=data, **data) for data in ports]
        self.network_mode = network_mode
        self.restart = restart
        self.healthcheck = HealthCheck(_raw=healthcheck, **healthcheck)
        self.hosts = hosts
        self.privileged = privileged
        self.log_config = log_config
        self.working_dir = working_dir
        self.after_start = after_start
        self.before_stop = before_stop
        self.backup_path = backup_path
        self._raw = _raw


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
    def fix_defaults(self, data):
        if 'name' not in data:
            data['name'] = data['appname']

        if 'base' in data:
            default_build_base = data['base']
            for build in data['builds'].values():
                if 'base' not in build:
                    build['base'] = default_build_base

        for _, entrypoint in data['entrypoints'].items():
            # set default working_dir to app's home
            if not entrypoint.get('working_dir'):
                entrypoint['working_dir'] = '/home/{}'.format(data['appname'])

            # if there's anything to be published to ELB, give em some free tcp
            # healthcheck, if there's no healthcheck defined at all
            publish_ports = entrypoint.get('ports')
            if publish_ports and not entrypoint.get('healthcheck'):
                entrypoint['healthcheck'] = {
                    'tcp_ports': [str(p['port']) for p in publish_ports],
                }

    @validates_schema(pass_original=True)
    def validate_misc(self, data, original_data):
        # check raw related fields
        raw = False if data.get('stages') else True
        if not raw and data.get('container_user'):
            raise ValidationError('cannot specify container_user because this release is not raw')
        if raw and not data.get('base'):
            raise ValidationError('this is a raw release, must specify base')

        if not data.get('base'):
            for build in data['builds'].values():
                if not build.get('base'):
                    raise ValidationError('either use a global base image as default build base, or specify base in each build stage')


class Specs(Jsonized):

    exclude_from_dump = ['crontab']

    def __init__(self, appname=None, name=None, entrypoints={}, dns=None,
                 hosts=None, stages=None, container_user=None, builds={},
                 volumes=None, base=None, subscribers=None,
                 erection_timeout=None, crontab=None, _raw=None):
        self.appname = appname
        self.name = name
        self.entrypoints = {entrypoint_name: Entrypoint(_raw=data, **data) for entrypoint_name, data in entrypoints.items()}
        self.dns = dns
        self.hosts = hosts
        self.stages = stages
        self.container_user = container_user
        self.builds = builds
        self.volumes = volumes
        self.base = base
        self.subscribers = subscribers
        self.erection_timeout = erection_timeout
        self.crontab = crontab
        self._raw = _raw
        for field_name in self.exclude_from_dump:
            del _raw[field_name]

    @classmethod
    def validate(cls, s):
        dic = yaml.load(s)
        unmarshal_result = SpecsSchema().load(dic)
        errors = unmarshal_result.errors
        if errors:
            raise ValidationError(str(errors))
        # validate build related clause
        declared_stages = set(dic['stages'])
        actual_build_stages = set(dic['builds'])
        if declared_stages != actual_build_stages:
            raise ValidationError('stages inconsistent with builds: {} vs {}'.format(declared_stages, actual_build_stages))

    @classmethod
    def from_dict(cls, dic):
        unmarshal_result = SpecsSchema().load(dic)
        data = unmarshal_result.data
        return cls(_raw=data, **data)

    @classmethod
    @memoize
    def from_string(cls, s):
        dic = yaml.load(s)
        return cls.from_dict(dic)
