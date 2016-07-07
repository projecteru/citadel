# coding: utf-8

import json
from datetime import datetime

from citadel.ext import db, rds
from citadel.libs.json import Jsonized


class BaseModelMixin(db.Model, Jsonized):

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created = db.Column(db.DateTime, default=datetime.now)
    updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def get(cls, id):
        return cls.query.get(id)

    @classmethod
    def get_multi(cls, ids):
        return [cls.get(i) for i in ids]

    @classmethod
    def get_all(cls, start=0, limit=20):
        q = cls.query.order_by(cls.id.desc())
        return q[start:start+limit]

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    def to_dict(self):
        return {
            'id': self.id,
            'created': self.created,
            'updated': self.updated,
        }


class PropsMixin(object):
    """丢redis里"""

    def get_uuid(self):
        raise NotImplementedError('Need uuid to idenify objects')

    @property
    def _property_key(self):
        return self.get_uuid() + '/property'

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
        return self.props.get(key, default)

    def set_props_item(self, key, value):
        props = self.props
        props[key] = value
        self.props = props

    def delete_props_item(self, key):
        props = self.props
        props.pop(key, None)
        self.props = props


class PropsItem(object):

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
