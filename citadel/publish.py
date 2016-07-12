# coding: utf-8

import json
import logging
from functools import partial
from etcd import EtcdException

from citadel.ext import rds, etcd
from citadel.libs.utils import handle_exception
from citadel.models.app import App
from citadel.models.container import Container


_log = logging.getLogger(__name__)
_APP_DISCOVERY_KEY = 'eru:discovery:published'


handle_etcd_exception = partial(handle_exception, (EtcdException, ValueError, KeyError))


class EtcdPublisher(object):
    """
    完整路径是 /eru/service-nodes/:podname/:appname
    为了方便其他人读, 直接把所有信息存放在 :appname 下
    """
    APP_PATH = '/eru/service-nodes/%s/%s'

    @classmethod
    @handle_etcd_exception()
    def read(cls, path):
        return etcd.read(path)

    @classmethod
    @handle_etcd_exception()
    def write(cls, path, value):
        return etcd.write(path, value)

    def get_app(self, appname, podname):
        path = self.APP_PATH % (podname, appname)
        r = self.read(path)
        return r and json.loads(r.value) or None

    def add_container(self, container):
        app = self.get_app(container.appname, container.podname) or {}

        addresses = container.get_ips()
        backends = container.get_backends()

        current_addresses = app.get(container.sha, {}).get(container.entrypoint, {}).get('addresses', [])
        current_backends = app.get(container.sha, {}).get(container.entrypoint, {}).get('backends', [])

        new_addresses = list(set(current_addresses) | set(addresses))
        new_backends = list(set(current_backends) | set(backends))

        entrypoint = app.setdefault(container.sha, {}).setdefault(container.entrypoint, {})
        entrypoint['addresses'] = new_addresses
        entrypoint['backends'] = new_backends

        path = self.APP_PATH % (container.podname, container.appname)
        self.write(path, json.dumps(app))

    def remove_container(self, container):
        app = self.get_app(container.appname, container.podname)
        if not app:
            return

        addresses = container.get_ips()
        backends = container.get_backends()

        current_addresses = app.get(container.sha, {}).get(container.entrypoint, {}).get('addresses', [])
        current_backends = app.get(container.sha, {}).get(container.entrypoint, {}).get('backends', [])

        new_addresses = list(set(current_addresses).difference(set(addresses)))
        new_backends = list(set(current_backends).difference(set(backends)))

        entrypoint = app.setdefault(container.sha, {}).setdefault(container.entrypoint, {})
        entrypoint['addresses'] = new_addresses
        entrypoint['backends'] = new_backends

        path = self.APP_PATH % (container.podname, container.appname)
        self.write(path, json.dumps(app))

    def publish_app(self, appname):
        app = App.get_by_name(appname)
        if not app:
            return

        ctable = {}
        for c in Container.get_by_app(app.name, limit=1000):
            ctable.setdefault(c.podname, []).append(c)

        for podname, containers in ctable.iteritems():
            data = {}
            for c in containers:
                if not c.is_alive or c.in_removal:
                    continue
                data.setdefault(c.sha, {}).setdefault(c.entrypoint, {}).setdefault('addresses', []).extend(c.get_ips())
                data.setdefault(c.sha, {}).setdefault(c.entrypoint, {}).setdefault('backends', []).extend(c.get_backends())
                data.setdefault(c.sha, {}).setdefault('_all', {}).setdefault('addresses', []).extend(c.get_ips())
                data.setdefault(c.sha, {}).setdefault('_all', {}).setdefault('backends', []).extend(c.get_backends())

            path = self.APP_PATH % (podname, appname)
            self.write(path, json.dumps(data))


publisher = EtcdPublisher()


def publish_to_service_discovery(*appnames):
    for appname in appnames:
        publisher.publish_app(appname)
        rds.publish(_APP_DISCOVERY_KEY, appname)
