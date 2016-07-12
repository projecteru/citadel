# coding: utf-8

import yaml
from citadel.libs.json import Jsonized


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
        return cls(data['bind'], data['ro'])


class Entrypoint(object):

    def __init__(self, command, ports, exposes, network_mode, mem_limit,
            restart, health_check, hosts, permdir, privileged, log_config):
        self.command = command
        self.ports = ports
        self.exposes = exposes
        self.network_mode = network_mode
        self.mem_limit = mem_limit
        self.restart = restart
        self.health_check = health_check
        self.hosts = hosts
        self.permdir = permdir
        self.privileged = privileged
        self.log_config = log_config

    @classmethod
    def from_dict(cls, data):
        command = data['cmd']
        ports = [Port.from_string(p) for p in data.get('ports', [])]
        exposes = [Expose.from_string(e) for e in data.get('exposes', [])]
        network_mode = data.get('network_mode')
        mem_limit = data.get('mem_limit')
        restart = data.get('restart')
        health_check = data.get('health_check')
        hosts = data.get('hosts', [])
        permdir = bool(data.get('permdir'))
        privileged = bool(data.get('privileged'))
        log_config = data.get('log_config', 'json-file')
        return cls(command, ports, exposes, network_mode, mem_limit, restart,
                health_check, hosts, permdir, privileged, log_config)


class Specs(Jsonized):

    def __init__(self, appname, entrypoints, build, volumes, binds, meta, base, raw):
        # raw to jsonize
        self.appname = appname
        self.entrypoints = entrypoints
        self.build = build
        self.volumes = volumes
        self.binds = binds
        self.meta = meta
        self.base = base
        self._raw = raw

    @classmethod
    def from_dict(cls, data):
        appname = data['appname']
        entrypoints = {key: Entrypoint.from_dict(value) for key, value in data.get('entrypoints', {}).iteritems()}
        build = data.get('build', [])
        volumes = data.get('volumes', [])
        binds = {key: Bind.from_dict(value) for key, value in data.get('binds', {}).iteritems()}
        meta = data.get('meta', {})
        base = data.get('base')
        return cls(appname, entrypoints, build, volumes, binds, meta, base, data)

    @classmethod
    def from_string(cls, string):
        data = yaml.load(string)
        return cls.from_dict(data)
