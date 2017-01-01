# -*- coding: utf-8 -*-
from datetime import datetime

from boltons.iterutils import remap
from flask import abort
from werkzeug.routing import BaseConverter, ValidationError


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
            abort(400, '`%s` must be in dict' % key)


def purge_none_val_from_dict(dic):
    return remap(dic, visit=lambda path, key, val: val is not None)
