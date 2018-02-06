# -*- coding: utf-8 -*-

import enum
import sqlalchemy
from datetime import datetime

from citadel.ext import db
from citadel.libs.datastructure import purge_none_val_from_dict
from citadel.models.base import BaseModelMixin, Enum34


class OPType(enum.Enum):
    REGISTER_RELEASE = 'register_release'
    BUILD_IMAGE = 'build_image'
    CREATE_ENV = 'create_env'
    DELETE_ENV = 'delete_env'
    CREATE_CONTAINER = 'create_container'
    REMOVE_CONTAINER = 'remove_container'
    UPGRADE_CONTAINER = 'upgrade_container'
    CREATE_ELB_INSTANCE = 'create_elb_instance'
    CREATE_ELB_ROUTE = 'create_elb_route'
    DELETE_ELB_ROUTE = 'delete_elb_route'


class OPLog(BaseModelMixin):

    __tablename__ = 'operation_log'
    container_id = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    zone = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    user_id = db.Column(db.Integer, nullable=False, default=0, index=True)
    appname = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    sha = db.Column(db.CHAR(64), nullable=False, default='', index=True)
    action = db.Column(Enum34(OPType))
    content = db.Column(db.JSON)

    @classmethod
    def get_by(cls, **kwargs):
        '''
        query operation logs, all fields could be used as query parameters
        '''
        purge_none_val_from_dict(kwargs)
        container_id = kwargs.pop('container_id', None)
        sha = kwargs.pop('sha', None)
        limit = kwargs.pop('limit', 200)
        time_window = kwargs.pop('time_window', None)

        filters = [getattr(cls, k)==v for k, v in kwargs.items()]

        if container_id:
            if len(container_id) < 7:
                raise ValueError('minimum container_id length is 7')
            filters.append(cls.container_id.like('{}%'.format(container_id)))

        if sha:
            if len(sha) < 7:
                raise ValueError('minimum sha length is 7')
            filters.append(cls.sha.like('{}%'.format(sha)))

        if time_window:
            left, right = time_window
            left = left or datetime.min
            right = right or datetime.now()
            filters.extend([cls.created >= left, cls.created <= right])

        return cls.query.filter(sqlalchemy.and_(*filters)).order_by(cls.id.desc()).limit(limit).all()

    @classmethod
    def create(cls, zone=None, container_id=None, user_id=None, appname=None,
               sha=None, action=None, content=None):
        op_log = cls(container_id=container_id, zone=zone, user_id=user_id,
                     appname=appname, sha=sha, action=action, content=content)
        db.session.add(op_log)
        db.session.commit()
        return op_log

    @property
    def verbose_action(self):
        return self.action.name

    @property
    def short_sha(self):
        return self.sha and self.sha[:7]
