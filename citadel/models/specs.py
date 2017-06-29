# -*- coding: utf-8 -*-
from numbers import Number

import yaml
from crontab import CronTab
from humanfriendly import InvalidTimespan, parse_timespan, parse_size
from humanize import naturalsize
from marshmallow import Schema, fields, ValidationError

from citadel.config import ZONE_CONFIG, DEFAULT_ZONE
from citadel.libs.jsonutils import Jsonized
from citadel.libs.utils import memoize


FIVE_MINUTES = parse_timespan('5m')


def validate_protocol(s):
    if s not in {'http', 'tcp'}:
        raise ValidationError('ELB port should talk tcp or http')


def validate_port(n):
    if not 0 < n <= 65535:
        raise ValidationError('Port must be 0-65,535')


def validate_network_mode(s):
    if s not in {'host', 'bridge'}:
        raise ValidationError('Network mode must be host or bridge')


def validate_restart(s):
    if s not in {'no', 'unless-stopped', 'always', 'on-failure'}:
        raise ValidationError('Bad restart policy: {}'.format(s))


def validate_http_code(n):
    if not 100 <= n <= 599:
        raise ValidationError('HTTP code should be 100-599')


def validate_log_config(s):
    if s not in {'json-file', 'none', 'syslog'}:
        raise ValidationError('Log config should choose from json-file, none, syslog')


def validate_zone(s):
    if s not in ZONE_CONFIG:
        raise ValidationError('Bad zone: {}'.format(s))


def validate_entrypoint_name(s):
    if '_' in s:
        raise ValidationError('Entrypoints must not contain underscore')


def validate_cpu(n):
    if n < 0:
        raise ValidationError('CPU must >=0')


def validate_user(username):
    from citadel.models.user import User
    try:
        if not User.get(username):
            raise ValidationError('Bad username in permitted_users: {}'.format(username))
    except RuntimeError:
        pass


def validate_elb_domain(s):
    if not len(s.split()) == 2:
        raise ValidationError('Bad ELB domain record, should be \'$ELB_NAME $DOMAIN\'')


def parse_single_port(port_string):
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
    unmarshal_result = PortSchema().load({'port': port, 'protocol': protocol})
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


def parse_combos(dic):
    """
    should re-write once marshmallow supports nested schema
    http://stackoverflow.com/questions/38048775/marshmallow-dict-of-nested-schema
    """
    for combo_name, combo_dic in dic.items():
        unmarshal_result = combo_schema.load(combo_dic)
        errors = unmarshal_result.errors
        if errors:
            raise ValidationError(str(errors))
        dic[combo_name] = unmarshal_result.data

    return dic


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


class PortSchema(Schema):
    protocol = fields.Str(validate=validate_protocol, missing='tcp')
    port = fields.Int(validate=validate_port, required=True)


class Port(Jsonized):
    def __init__(self, protocol=None, port=None, _raw=None):
        self.protocol = protocol
        self.port = port
        self._raw = _raw


class EntrypointSchema(Schema):
    cmd = fields.Str(attribute='command', required=True)
    ports = fields.Function(deserialize=parse_port_list, missing=[])
    network_mode = fields.Str(validate=validate_network_mode, missing='bridge')
    restart = fields.Str(validate=validate_restart)
    healthcheck_url = fields.Str()
    healthcheck_port = fields.Int(validate=validate_port)
    healthcheck_expected_code = fields.Int(validate=validate_http_code)
    hosts = fields.List(fields.Str())
    privileged = fields.Bool(missing=False)
    log_config = fields.Str(validate=validate_log_config)
    working_dir = fields.Str()
    backup_path = fields.List(fields.Str(), missing=[])


class Entrypoint(Jsonized):
    def __init__(self, command=None, ports=None, network_mode=None,
                 restart=None, healthcheck_url=None, healthcheck_port=None,
                 healthcheck_expected_code=None, hosts=None, privileged=None,
                 log_config=None, working_dir=None, backup_path=None,
                 _raw=None):
        self.command = command
        self.ports = [Port(_raw=_raw, **data) for data in ports]
        self.network_mode = network_mode
        self.restart = restart
        self.hosts = hosts
        self.privileged = privileged
        self.log_config = log_config
        self.working_dir = working_dir
        self.backup_path = backup_path


entrypoint_schema = EntrypointSchema()


class ComboSchema(Schema):
    zone = fields.Str(validate=validate_zone, missing=DEFAULT_ZONE)
    podname = fields.Str(required=True)
    nodename = fields.Str()
    entrypoint = fields.Str(validate=validate_entrypoint_name, required=True)
    envname = fields.Str(missing='')
    cpu = fields.Float(required=True, validate=validate_cpu)
    memory = fields.Function(deserialize=parse_memory, required=True)
    count = fields.Int(missing=1)
    extra_env = fields.Function(deserialize=parse_extra_env, missing={})
    networks = fields.List(fields.Str(), missing=[])
    elb = fields.List(fields.Str())


class Combo(Jsonized):
    def __init__(self, zone=None, podname=None, nodename=None, entrypoint=None,
                 envname=None, cpu=None, memory=None, count=None,
                 extra_env=None, networks=None, elb=None, _raw=None):
        self.zone = zone
        self.podname = podname
        self.nodename = nodename
        self.entrypoint = entrypoint
        self.envname = envname
        self.cpu = cpu
        self.memory = memory
        self.count = count
        self.extra_env = extra_env
        self.networks = networks
        self.elb = elb

    @property
    def memory_str(self):
        return naturalsize(self.memory, binary=True)

    @property
    def env_string(self):
        return ';'.join('%s=%s' % (k, v) for k, v in self.extra_env.items())


combo_schema = ComboSchema()


class SpecsSchema(Schema):
    appname = fields.Str(required=True)
    entrypoints = fields.Function(deserialize=parse_entrypoints, required=True)
    build = fields.List(fields.Str())
    volumes = fields.List(fields.Str())
    base = fields.Str(required=True)
    combos = fields.Function(deserialize=parse_combos, missing={})
    permitted_users = fields.List(fields.Str(validate=validate_user), missing=[])
    subscribers = fields.Str(required=True)
    erection_timeout = fields.Function(deserialize=better_parse_timespan, missing=FIVE_MINUTES)
    smooth_upgrade = fields.Bool(missing=True)
    crontab = fields.Function(deserialize=parse_crontab, missing=[])

class Specs(Jsonized):

    """Encapsule details regarding object creation, and backward compatibility.
    Note that all the default arguments here should be None, and implement the
    actual default arguments in marshmallow, except the ones with backward
    compatibility issues"""

    exclude_from_dump = ['crontab']

    def __init__(self, appname=None, entrypoints=None, build=None, volumes=None,
                 base=None, combos={}, permitted_users=None, subscribers=None,
                 erection_timeout=None, smooth_upgrade=None, crontab=None,
                 _raw=None):
        self.appname = appname
        self.entrypoints = {entrypoint_name: Entrypoint(_raw=data, **data) for entrypoint_name, data in entrypoints.items()}
        self.build = build
        self.volumes = volumes
        self.base = base
        self.combos = {combo_name: Combo(_raw=data, **data) for combo_name, data in combos.items()}
        self.permitted_users = set(permitted_users)
        self.subscribers = subscribers
        self.erection_timeout = erection_timeout
        self.smooth_upgrade = smooth_upgrade
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
        if 'mount_paths' in dic or 'binds' in dic or any(['permdir' in entrypoint for entrypoint in dic.get('entrypoint', {}).values()]):
            raise ValidationError('mount_paths, permdir, binds are no longer supported, use volumes instead, see http://platform.docs.ricebook.net/citadel/docs/user-docs/specs.html')

    @classmethod
    @memoize
    def from_string(cls, s):
        dic = yaml.load(s)
        unmarshal_result = SpecsSchema().load(dic)
        data = unmarshal_result.data
        return cls(_raw=data, **data)
