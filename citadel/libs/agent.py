# -*- coding: utf-8 -*-
import json

import requests
from requests.exceptions import ReadTimeout, ConnectionError, ConnectTimeout

from citadel.config import AGENT_PORT


class EruAgentError(Exception):
    pass


class EruAgentClient:

    def __init__(self, addr, port=AGENT_PORT):
        self.addr = addr
        self.port = port

    def log(self, appname):
        """获取日志, 流形式返回, 这里就随便包装下就可以了, 其实客户端完全可以直接连接..."""
        path = 'http://%s:%s/log/' % (self.addr, self.port)
        try:
            resp = requests.get(path, params={'app': appname}, stream=True, timeout=5)
            for line in resp.iter_lines():
                try:
                    yield json.loads(line)
                except ValueError as e:
                    raise EruAgentError(str(e))
        except (ReadTimeout, ConnectTimeout):
            raise EruAgentError('Read Timeout')
        except ConnectionError:
            raise EruAgentError('ConnectionError, Eru Agent may not working correctly')
