# -*- coding: utf-8 -*-
import json

import enum
import sqlalchemy.types as types
from flask import g
from flask_sqlalchemy import sqlalchemy as sa

from citadel.ext import db
from citadel.models.base import BaseModelMixin


class JsonType(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, engine):
        try:
            return json.dumps(value)
        except ValueError:
            return '{}'

    def process_result_value(self, value, engine):
        try:
            return json.loads(value)
        except ValueError:
            return {}


class Enum34(types.TypeDecorator):
    impl = types.Integer

    def __init__(self, enum_class, *args, **kwargs):
        super(Enum34, self).__init__(*args, **kwargs)
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value not in self.enum_class:
            raise ValueError("\"%s\"is not a valid enum value" % repr(value))
        return value.value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.enum_class(value)
        return None


class OPType(enum.Enum):

    REGISTER_RELEASE = 0
    BUILD_IMAGE = 1
    CREATE_ENV = 2
    DELETE_ENV = 3
    CREATE_CONTAINER = 4
    REMOVE_CONTAINER = 5
    UPGRADE_CONTAINER = 6
    CREATE_ELB_INSTANCE = 7
    CREATE_ELB_ROUTE = 8
    DELETE_ELB_ROUTE = 9


class OPLog(BaseModelMixin):

    __tablename__ = 'operation_log'
    user_id = db.Column(db.Integer, nullable=True, index=True)
    appname = db.Column(db.CHAR(64), nullable=True, index=True)
    sha = db.Column(db.CHAR(64), nullable=True, index=True)
    action = db.Column(Enum34(OPType))
    content = db.Column(JsonType, default={})

    @classmethod
    def get_by(cls, user_id=None, appname=None, sha=None, action=None, time_window=None):
        """filter OPLog by user, action, or a tuple of 2 datetime as timewindow"""
        filters = []
        if user_id:
            filters.append(cls.user_id == user_id)

        if appname:
            filters.append(cls.appname == appname)

        if sha:
            filters.append(cls.sha.like('{}%'.format(sha)))

        if action:
            filters.append(cls.action == action)

        if time_window:
            start, end = time_window
            filters.extend([cls.dt >= start, cls.dt <= end])

        return cls.query.filter(sa.and_(*filters)).order_by(sa.desc(cls.dt)).all()

    @classmethod
    def create(cls, action, appname=None, sha=None, content=None):
        try:
            user_id = g.user.id
        except:
            user_id = 0

        op_log = cls(user_id=user_id,
                     appname=appname,
                     sha=sha,
                     action=action,
                     content=content)
        db.session.add(op_log)
        db.session.commit()
        return op_log

    @property
    def verbose_action(self):
        return self.action.name
