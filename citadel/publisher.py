# -*- coding: utf-8 -*-
import json
import os

from citadel.ext import get_etcd
from citadel.libs.utils import handle_etcd_exception


class Publisher:

    """publish container to etcd if publish_path is defined in app.yaml"""

    @classmethod
    @handle_etcd_exception()
    def write(cls, zone, path, dic):
        return get_etcd(zone).write(path, json.dumps(dic))

    @classmethod
    @handle_etcd_exception()
    def list_addrs(cls, zone, path):
        res = get_etcd(zone).read(path)
        nodes = [leave.key.rsplit('/', 1)[-1] for leave in res.leaves]
        return nodes

    @classmethod
    @handle_etcd_exception()
    def delete(cls, zone, path):
        return get_etcd(zone).delete(path)

    @classmethod
    def add_container(cls, container):
        publish_path = container.publish_path
        if not publish_path:
            return
        for addr in container.get_backends():
            path = os.path.join(publish_path, addr)
            cls.write(container.zone, path, 'true')

    @classmethod
    def remove_container(cls, container):
        try:
            publish_path = container.publish_path
        except KeyError:
            return
        if not publish_path:
            return
        for addr in container.get_backends():
            path = os.path.join(publish_path, addr)
            cls.delete(container.zone, path)
