# -*- coding: utf-8 -*-
import enum
import sqlalchemy
from flask import g

from citadel.ext import db
from citadel.models.base import BaseModelMixin, Enum34
from citadel.models.user import get_user


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
    zone = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    user_id = db.Column(db.Integer, nullable=False, default=0, index=True)
    appname = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    sha = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    action = db.Column(Enum34(OPType))
    content = db.Column(db.JSON)

    @classmethod
    def get_by(cls, user_id=None, appname=None, sha=None, action=None, time_window=None, start=0, limit=100):
        """filter OPLog by user, action, or a tuple of 2 datetime as timewindow"""
        filters = [cls.zone == g.zone | cls.zone == '']
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

        return cls.query.filter(sqlalchemy.and_(*filters)).order_by(cls.id.desc()).offset(start).limit(limit).all()

    @classmethod
    def create(cls, user_id, action, appname='', sha='', zone='', content=None):
        if content is None:
            content = {}

        op_log = cls(zone=zone,
                     user_id=user_id,
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

    @property
    def user_real_name(self):
        user = get_user(self.user_id)
        return user and user.real_name

    @property
    def short_sha(self):
        return self.sha and self.sha[:7]
