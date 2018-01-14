# coding: utf-8

import json
import logging
from datetime import datetime
from flask_sqlalchemy import sqlalchemy as sa
from marshmallow import Schema, validates_schema, ValidationError
import sqlalchemy.orm.exc
import sqlalchemy.types as types
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from citadel.ext import db, rds
from citadel.libs.jsonutils import Jsonized
from citadel.libs.utils import logger


_missing = object()
_logger = logging.getLogger(__name__)


class BaseModelMixin(db.Model, Jsonized):

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created = db.Column(db.DateTime, server_default=sa.sql.func.now())
    updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def create(cls, **kwargs):
        b = cls(**kwargs)
        try:
            db.session.add(b)
            db.session.commit()
            return b
        except SQLAlchemyError as e:
            _logger.error('Create %s error: %s', cls, e)
            db.session.rollback()
            return

    @classmethod
    def get(cls, id):
        return cls.query.get(id)

    @classmethod
    def get_multi(cls, ids):
        return [cls.get(i) for i in ids]

    mget = get_multi

    @classmethod
    def get_all(cls, start=0, limit=20):
        q = cls.query.order_by(cls.id.desc())
        if not any([start, limit]):
            return q.all()
        return q[start:start + limit]

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except sqlalchemy.orm.exc.ObjectDeletedError:
            logger.warn('Error during deleting: Object %s already deleted', self)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self):
        return hash((self.__class__, self.id))

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class PropsMixin:
    """丢redis里"""

    def get_uuid(self):
        raise NotImplementedError('Need uuid to idenify objects')

    @property
    def _property_key(self):
        """因为是redis还是改用redis风格的key吧"""
        return self.get_uuid() + ':property'

    def get_props(self):
        props = rds.get(self._property_key) or '{}'
        return json.loads(props)

    def set_props(self, props):
        rds.set(self._property_key, json.dumps(props))

    def destroy_props(self):
        rds.delete(self._property_key)

    props = property(get_props, set_props, destroy_props)

    def update_props(self, **kw):
        props = self.props
        props.update(kw)
        self.props = props

    def get_props_item(self, key, default=None):
        r = self.props.get(key, _missing)
        if r is not _missing:
            return r
        if callable(default):
            return default()
        return default

    def set_props_item(self, key, value):
        props = self.props
        props[key] = value
        self.props = props

    def delete_props_item(self, key):
        props = self.props
        props.pop(key, None)
        self.props = props


class PropsItem:

    def __init__(self, name, default=None, type=None):
        self.name = name
        self.default = default
        self.type = type

    def __get__(self, obj, obj_type):
        r = obj.get_props_item(self.name, self.default)
        if self.type:
            r = self.type(r)

        return r

    def __set__(self, obj, value):
        obj.set_props_item(self.name, value)

    def __delete__(self, obj):
        obj.delete_props_item(self.name)


class Enum34(types.TypeDecorator):
    impl = types.Integer

    def __init__(self, enum_class, *args, **kwargs):
        super(Enum34, self).__init__(*args, **kwargs)
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value not in self.enum_class:
            raise ValueError("'%s' is not a valid enum value" % repr(value))
        return value.value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.enum_class(value)
        return None


class StrictSchema(Schema):

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, data, original_data):
        unknown = set(original_data) - set(self.fields)
        if unknown:
            raise ValidationError('Unknown fields: {}, please check the docs'.format(unknown))

    class Meta:
        strict = True
