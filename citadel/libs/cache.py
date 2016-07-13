# coding: utf-8

import cPickle
import functools
import inspect

from citadel.ext import rds


ONE_DAY = 86400
ONE_HOUR = 3600


def cache(fmt, ttl=None):
    def _cache(f):
        @functools.wraps(f)
        def _(*args, **kwargs):
            ags = inspect.getargspec(f)
            kw = dict(zip(ags.args, args))
            kw.update(kwargs)

            key = fmt.format(**kw)
            value = rds.get(key)
            if value is not None:
                return cPickle.loads(value)

            r = f(*args, **kwargs)
            if r is not None:
                rds.set(key, cPickle.dumps(r), ex=ttl)

            return r
        return _
    return _cache
