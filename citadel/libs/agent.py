# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

import ipaddress
import requests
from requests.exceptions import ReadTimeout, ConnectionError, ConnectTimeout

from citadel.config import AGENT_PORT
from citadel.ext import rds


VIP_NETWORK = u'10.215.247.0/24'
VIP_RECORD = 'citadel:vip:record'
VIPS = ipaddress.ip_network(VIP_NETWORK).hosts()
VIP_POOL = set([ip.exploded for ip in list(VIPS)])


def generate_vip():
    used_vip = set(rds.hkeys(VIP_RECORD))
    available_vip = VIP_POOL - used_vip
    return available_vip.pop()


def list_vip_from_redis():
    return rds.hgetall(VIP_RECORD)


class EruAgentError(Exception):
    pass


class EruAgentClient(object):

    def __init__(self, addr, port=AGENT_PORT):
        self.addr = addr
        self.port = port
        self.base = 'http://%s:%s' % (addr, port)

    def log(self, appname):
        url = self.base + '/log/'
        try:
            resp = requests.get(url, params={'app': appname}, stream=True, timeout=5)
            for line in resp.iter_lines():
                try:
                    yield json.loads(line)
                except ValueError as e:
                    raise EruAgentError(str(e))
        except (ReadTimeout, ConnectTimeout) as e:
            raise EruAgentError(str(e))
        except ConnectionError as e:
            raise EruAgentError(str(e))

    def _do(self, path, method, *args, **kwargs):
        url = self.base + path
        func = requests.post if method == 'POST' else requests.get
        try:
            resp = func(url, *args, **kwargs)
        except (ReadTimeout, ConnectTimeout) as e:
            raise EruAgentError(str(e))
        except ConnectionError:
            raise EruAgentError(str(e))

        return resp

    def set_vip(self, vip, interface='eth0'):
        resp = self._do('/setvip/', 'POST', data={'vip': vip, 'interface': interface})
        resp.raise_for_status()
        rds.hset(VIP_RECORD, vip, self.addr)

    def del_vip(self, vip, interface='eth0'):
        resp = self._do('/delvip/', 'POST', data={'vip': vip, 'interface': interface})
        resp.raise_for_status()
        rds.hdel(VIP_RECORD, vip)

    def exists_vip(self, vip, interface='eth0'):
        resp = self._do('/checkvip/', 'GET', params={'vip': vip, 'interface': interface})
        resp.raise_for_status()
        return resp.json()['status'] == 'VipExists'
