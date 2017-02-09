# -*- coding: utf-8 -*-
import json
import os

from citadel.ext import get_etcd
from citadel.libs.utils import handle_etcd_exception


class Publisher(object):

    """publish container to etcd if publish_path is defined in app.yaml"""

    @classmethod
    @handle_etcd_exception()
    def write(cls, zone, path, dic):
        return get_etcd(zone).write(path, json.dumps(dic))

    @classmethod
    @handle_etcd_exception()
    def read(cls, zone, path):
        res = get_etcd(zone).read(path)
        return res and json.loads(res)

    @classmethod
    @handle_etcd_exception()
    def delete(cls, zone, path):
        return get_etcd(zone).delete(path)

    @classmethod
    def add_container(cls, container):
        publish_path = container.release.entrypoints[container.entrypoint].publish_path
        if not publish_path:
            return
        for addr in container.get_backends():
            path = os.path.join(publish_path, addr)

    @classmethod
    def remove_container(cls, container):
        publish_path = container.release.entrypoints[container.entrypoint].publish_path
        for addr in container.get_backends():
            path = os.path.join(publish_path, addr)
            cls.delete(container.zone, path)
