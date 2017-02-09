# -*- coding: utf-8 -*-
from datetime import timedelta

import yaml
from humanfriendly import InvalidTimespan, parse_timespan, parse_size

from citadel.config import DEFAULT_ZONE
from citadel.libs.jsonutils import Jsonized
from citadel.libs.utils import make_unicode


class SpecsError(Exception):
    pass


class Port(object):

    def __init__(self, protocol, port):
        self.protocol = protocol
        self.port = port

    @classmethod
    def from_string(cls, data):
        ps = data.split('/', 1)
        protocol = 'tcp' if len(ps) == 1 else ps[1]
        port = int(ps[0])
        return cls(protocol, port)


class Expose(object):

    def __init__(self, container_port, host_port):
        self.container_port = container_port
        self.host_port = host_port

    @classmethod
    def from_string(cls, data):
        ps = data.split(':')
        container_port = Port.from_string(ps[0])
        host_port = Port.from_string(ps[1])
        return cls(container_port, host_port)


class Bind(object):

    def __init__(self, path, ro):
        self.path = path
        self.ro = ro

    @classmethod
    def from_dict(cls, data):
        return cls(data['bind'], data.get('ro', True))


class Entrypoint(object):

    def __init__(self, command, ports, exposes, network_mode, restart, health_check, hosts, permdir, privileged, log_config, working_dir, publish_path):
        self.command = command
        self.ports = ports
        self.exposes = exposes
        self.network_mode = network_mode
        self.restart = restart
        self.health_check = health_check
        self.hosts = hosts
        self.permdir = permdir
        self.privileged = privileged
        self.log_config = log_config
        self.working_dir = working_dir
        self.publish_path = publish_path

    @classmethod
    def from_dict(cls, data):
        command = data['cmd']
        ports = [Port.from_string(p) for p in data.get('ports') or []]
        exposes = [Expose.from_string(e) for e in data.get('exposes', ())]
        network_mode = data.get('network_mode')
        restart = data.get('restart')
        health_check = data.get('health_check')
        hosts = data.get('hosts', ())
        permdir = bool(data.get('permdir'))
        privileged = bool(data.get('privileged'))
        log_config = data.get('log_config', 'json-file')
        working_dir = data.get('working_dir', '')
        publish_path = data.get('publish_path', '')
        return cls(command, ports, exposes, network_mode, restart, health_check, hosts, permdir, privileged, log_config, working_dir, publish_path)


class Combo(object):

    def __init__(self, zone, podname, nodename, entrypoint, envname='', cpu=0, memory='0', count=1, envs={}, raw=False, networks=(), permitted_users=(), elb=()):
        self.zone = zone
        self.podname = podname
        self.nodename = nodename
        self.entrypoint = entrypoint
        self.envname = envname
        self.cpu = cpu
        # could be int or string (like '512Mib', '512MB', both considered binary)
        self.memory = parse_size(memory, binary=True) if isinstance(memory, basestring) else memory
        self.memory_str = memory
        self.count = count
        self.envs = envs
        self.raw = raw
        self.networks = tuple(networks)
        self.permitted_users = tuple(permitted_users)
        self.elb = tuple(elb)

    @classmethod
    def from_dict(cls, data):
        zone = data.get('zone', DEFAULT_ZONE)
        podname = data['podname']
        nodename = data.get('nodename', '')
        entrypoint = data['entrypoint']
        envname = data.get('envname', '')
        cpu = float(data.get('cpu', 1))
        memory = data.get('memory', '0')
        count = int(data.get('count', 1))
        raw = bool(data.get('raw', False))
        networks = data.get('networks', ())
        permitted_users = data.get('permitted_users', ())
        elb = data.get('elb', ())

        envs = data.get('envs', {})
        if isinstance(envs, basestring):
            parts = envs.split(';')
            envs = {}
            for p in parts:
                if not p:
                    continue
                k, v = p.split('=', 1)
                envs[k] = v

        return cls(zone, podname, nodename, entrypoint, envname, cpu, memory, count, envs, raw, networks, permitted_users, elb)

    def allow(self, user):
        if not self.permitted_users:
            return True
        return user in self.permitted_users

    def env_string(self):
        return ';'.join('%s=%s' % (k, v) for k, v in self.envs.iteritems())


class Specs(Jsonized):

    def __init__(self, appname, entrypoints, build, volumes, binds, meta, base, mount_paths, combos, permitted_users, subscribers, erection_timeout, raw):
        # raw to jsonize
        self.appname = appname
        self.entrypoints = entrypoints
        self.build = build
        self.volumes = volumes
        self.binds = binds
        self.meta = meta
        self.base = base
        self.mount_paths = mount_paths
        self.combos = combos
        self.permitted_users = permitted_users
        self.subscribers = subscribers
        self.erection_timeout = erection_timeout
        self._raw = raw

    @classmethod
    def from_dict(cls, data):
        appname = data['appname']
        entrypoints = {key: Entrypoint.from_dict(value) for key, value in data.get('entrypoints', {}).iteritems()}
        build = data.get('build', ())
        try:
            erection_timeout = parse_timespan(str(data.get('erection_timeout', '5m')))
        except InvalidTimespan:
            erection_timeout = timedelta(minutes=5)

        # compatibility note:
        # old apps sometimes write: build: 'echo something'
        if isinstance(build, basestring):
            build = build,

        volumes = data.get('volumes', ())
        binds = {key: Bind.from_dict(value) for key, value in data.get('binds', {}).iteritems()}
        meta = data.get('meta', {})
        base = data.get('base')
        mount_paths = data.get('mount_paths', ())
        subscribers = data.get('subscribers', '')
        combos = {key: Combo.from_dict(value) for key, value in data.get('combos', {}).iteritems()}

        # permitted_users could be defined in both combos and specs
        permitted_user_list = [combo.permitted_users for combo in combos.values()]
        combos_permitted_users = tuple(u for g in permitted_user_list for u in g)
        app_permitted_users = tuple(data.get('permitted_users', ()))
        all_permitted_users = frozenset(combos_permitted_users + app_permitted_users)

        return cls(appname, entrypoints, build, volumes, binds, meta, base, mount_paths, combos, all_permitted_users, subscribers, erection_timeout, data)

    @classmethod
    def from_string(cls, string):
        data = yaml.load(string)
        return cls.from_dict(data)

    @classmethod
    def validate_specs_yaml(cls, s):
        """will raise yaml.parser.parser.ParserError or SpecsError"""
        specs = cls.from_string(s)
        # validate permitted_users
        from citadel.models.user import User
        for username in specs.permitted_users:
            if not User.get(username):
                raise SpecsError(u'Bad username in permitted_users: {}'.format(make_unicode(username)))
