# coding: utf-8

import yaml
from citadel.libs.json import Jsonized
from citadel.libs.utils import to_number


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
            restart, health_check, hosts, permdir, privileged, log_config, working_dir):
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
        self.working_dir = working_dir

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
        working_dir = data.get('working_dir', '')
        return cls(command, ports, exposes, network_mode, mem_limit, restart,
                health_check, hosts, permdir, privileged, log_config, working_dir)


class Combo(object):

    def __init__(self, podname, entrypoint, envname='', cpu=0, memory='0',
            count=1, envs={}, raw=False, networks=[], permitted_users=[]):
        self.podname = podname
        self.entrypoint = entrypoint
        self.envname = envname
        self.cpu = cpu
        self.memory = to_number(memory)
        self.memory_str = memory
        self.count = count
        self.envs = envs
        self.raw = raw
        self.networks = networks
        self.permitted_users = permitted_users

    @classmethod
    def from_dict(cls, data):
        podname = data['podname']
        entrypoint = data['entrypoint']
        envname = data.get('envname', '')
        cpu = float(data.get('cpu', 1))
        memory = data.get('memory', '0')
        count = int(data.get('count', 1))
        raw = bool(data.get('raw', False))
        networks = data.get('networks', [])
        permitted_users = data.get('permitted_users', [])

        envs = data.get('envs', {})
        if isinstance(envs, basestring):
            parts = envs.split(';')
            envs = {}
            for p in parts:
                if not p:
                    continue
                k, v = p.split('=', 1)
                envs[k] = v

        return cls(podname, entrypoint, envname, cpu, memory,
                count, envs, raw, networks, permitted_users)

    def allow(self, user):
        if not self.permitted_users:
            return True
        return user in self.permitted_users

    def env_string(self):
        return ';'.join('%s=%s' % (k, v) for k, v in self.envs.iteritems())


class Specs(Jsonized):

    def __init__(self, appname, entrypoints, build, volumes, binds, meta, base, mount_paths, combos, raw):
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
        mount_paths = data.get('mount_paths', [])
        combos = {key: Combo.from_dict(value) for key, value in data.get('combos', {}).iteritems()}
        return cls(appname, entrypoints, build, volumes, binds, meta, base, mount_paths, combos, data)

    @classmethod
    def from_string(cls, string):
        data = yaml.load(string)
        return cls.from_dict(data)
