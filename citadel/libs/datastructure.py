# -*- coding: utf-8 -*-
import operator
import time
from datetime import datetime, timedelta
from numbers import Number
from pprint import pformat

import wrapt
from boltons.iterutils import remap
from flask import abort
from humanfriendly import parse_timespan
from pyparsing import Literal, Word, ZeroOrMore, Forward, nums, oneOf, Group, alphanums, Regex, alphas
from werkzeug.routing import BaseConverter, ValidationError

from citadel.config import CITADEL_TACKLE_EXPRESSION_KEY
from citadel.ext import rds
from citadel.libs.utils import logger


class DateConverter(BaseConverter):
    """Extracts a ISO8601 date from the path and validates it."""

    regex = r'\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return value.strftime('%Y-%m-%d')


class AbortDict(dict):
    """类似request.form[key], 但是用来封装request.get_json()"""

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            abort(400, 'Missing argument %s' % key)


def purge_none_val_from_dict(dic):
    return remap(dic, visit=lambda path, key, val: val is not None)


class SmartStatus(object):

    """
    I have a dict of data, and I can evaluate DSL upon my data
    """
    def __init__(self, name=None, status_dic=None):
        self._name = name
        self._status_dic = dict(status_dic) if isinstance(status_dic, dict) else {}

        lpar = Literal('(').suppress()
        rpar = Literal(')').suppress()

        op = oneOf(' '.join([k for k in self._operator_map.keys()]))
        op.setParseAction(self._get_operator_func)

        # digits
        d = Word(nums + '.')
        d.setParseAction(lambda l: [float(i) for i in l])
        # something like 3m, 50s, see
        # https://humanfriendly.readthedocs.io/en/latest/#humanfriendly.parse_timespan
        td = Regex(r'[\d]+[a-zA-Z]+')
        td.setParseAction(self._parse_timedeltas)
        # something like cpu_usage_rate, vnbe0.inbytes
        metric = Word(alphas, alphanums + '._')
        # order matters
        any_v = td | metric | d

        self.expr = Forward()
        atom = any_v | Group(lpar + self.expr + rpar)
        self.expr << atom + ZeroOrMore(op + self.expr)

    def __str__(self):
        return '{}:\n{}'.format(self.name, pformat(self._status_dic, width=160))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, var):
        self._name = var

    @property
    def status_dic(self):
        return self._status_dic

    @status_dic.setter
    def status_dic(self, dic):
        self._status_dic = dic

    @property
    def _operator_map(self):
        return {
            '<'  : self._peek_value(operator.lt),
            '<=' : self._peek_value(operator.le),
            '==' : self._peek_value(operator.eq),
            '!=' : self._peek_value(operator.ne),
            '>=' : self._peek_value(operator.ge),
            '>'  : self._peek_value(operator.gt),
            '*'  : self._last_for,
        }

    def _parse_timedeltas(self, l):
        return [self._parse_timedelta(s) for s in l]

    def _parse_timedelta(self, td_str):
        seconds = parse_timespan(td_str)
        return timedelta(seconds=seconds)

    def _get_value_or_make_float(self, val):
        if isinstance(val, Number):
            return val

        return self.status_dic[val]

    def _peek_value(self, wrapped):
        """wrap operator comparison functions so that arguments will be
        substituted during runtime
        if value is number, return as-is, if not, treat as dict key in self._status_dic
        """
        @wrapt.decorator
        def wrapper(wrapped, ins, args, kwargs):
            lv, rv = [self._get_value_or_make_float(v) for v in args]
            result = wrapped(lv, rv, **kwargs)
            return result
        return wrapper(wrapped)

    @staticmethod
    def _make_comparison_expression_key(*parsed_group):
        str_list = [item.__name__ if callable(item) else item for item in parsed_group]
        key = CITADEL_TACKLE_EXPRESSION_KEY.format(*str_list)
        return key

    def _last_for(self, lval, threshold):
        comparison_expression_key = self._make_comparison_expression_key(*lval)
        eval_result = self._eval_expression(lval)
        logger.debug('Expression %s evaluated to be %s', lval, eval_result)
        if eval_result is True:
            now = datetime.now()
            if comparison_expression_key in rds:
                # redis 里标记了，拿出来比较一下，达到了阈值就返回True
                ts = float(rds.get(comparison_expression_key))
                marked_at = datetime.fromtimestamp(ts)
                delta = now - marked_at
                if delta >= threshold:
                    rds.delete(comparison_expression_key)
                    return True
            else:
                # redis 里没标记，那就是第一次出现，记下时间
                now_ts = time.mktime(now.utctimetuple())
                logger.debug('Marking comparison_expression_key: %s, value %s, expire in %s', comparison_expression_key, now_ts, threshold)
                rds.setex(comparison_expression_key, now_ts, threshold * 2)
        else:
            # 发现一次不满足条件，前功尽弃
            rds.delete(comparison_expression_key)

        return False

    def _get_operator_func(self, operator_str_list):
        return [self._operator_map[op_str] for op_str in operator_str_list]

    def _eval_expression(self, expression):
        """expression is a parsed dsl list"""
        lval, func, rval = expression
        return func(lval, rval)

    def eval_dsl(self, expr_str):
        """
        :param expr_str: str, like '(cpu_usage_rate > 0.8) * 3m'
        :returns: bool
        """
        parsed = self.expr.parseString(expr_str)
        return self._eval_expression(parsed)

    def eval_expressions(self, exprs):
        return [expr for expr in exprs if self.eval_dsl(expr)]
