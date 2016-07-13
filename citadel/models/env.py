# coding: utf-8

import json
from citadel.ext import rds
from citadel.libs.json import Jsonized

_KEY = 'core-api:app:%s:env'


class Environment(dict):

    def __init__(self, appname, envname, **kwargs):
        dict.__init__(self, kwargs)
        self.appname = appname
        self.envname = envname

    @classmethod
    def create(cls, appname, envname, **kwargs):
        env = cls(appname, envname, **kwargs)
        env.save()
        return env

    @classmethod
    def get_by_app_and_env(cls, appname, envname):
        r = rds.hget(_KEY % appname, envname)
        if not r:
            return
        return cls(appname, envname, **json.loads(r))

    @classmethod
    def get_by_app(cls, appname):
        r = rds.hkeys(_KEY % appname)
        return [cls.get_by_app_and_env(appname, env) for env in r]

    def save(self):
        rds.hset(_KEY % self.appname, self.envname, json.dumps(self))

    def delete(self):
        rds.hdel(_KEY % self.appname, self.envname)

    def to_env_vars(self):
        """外部调用需要的['A=1', 'B=var=1']这种格式"""
        return ['%s=%s' % (k, v) for k, v in self.iteritems()]

    def to_jsonable(self):
        """自己是个dict, 轮不到Jsonized"""
        return EnvironmentJSON(self.appname, self.envname, self)


class EnvironmentJSON(Jsonized):
    """json.dumps的顺序还轮不到Jsonized, 所以只好再包一个单纯的Jsonized"""

    def __init__(self, appname, envname, kw):
        self._raw = kw
        self.appname = appname
        self.envname = envname

    def to_dict(self):
        return {
            'vars': self._raw,
            'appname': self.appname,
            'envname': self.envname,
        }
