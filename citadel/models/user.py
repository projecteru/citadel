# -*- coding: utf-8 -*-

from authlib.client.apps import github
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from citadel.config import OAUTH_APP_NAME
from citadel.ext import db, fetch_token
from citadel.models.base import BaseModelMixin


def get_current_user():
    token = fetch_token(OAUTH_APP_NAME)
    if token:
        user = User.get_by_access_token(token['access_token'])
        if not user:
            authlib_user = github.fetch_user()
            return User.from_authlib_user(authlib_user)
        return user
    return None


class User(BaseModelMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.CHAR(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    access_token = db.Column(db.CHAR(60), nullable=True, index=True)
    privileged = db.Column(db.Integer, default=0)
    data = db.Column(db.JSON)

    @classmethod
    def create(cls, id=None, name=None, email=None, access_token=None,
               privileged=0, data=None):
        user = cls(id=id, name=name, email=email, data=data,
                   access_token=access_token)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise
        return user

    def __str__(self):
        return '{class_} {u.id} {u.name}'.format(
            class_=self.__class__,
            u=self,
        )

    @classmethod
    def get_by_access_token(cls, access_token):
        if not access_token:
            # access_token could be missing so this method is expected to be
            # called with access_token=None a lot, better check this before
            # initiating database query
            return None
        return cls.query.filter_by(access_token=access_token).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def from_authlib_user(cls, authlib_user):
        user = cls.query.filter_by(id=authlib_user.id).first()
        token = fetch_token(OAUTH_APP_NAME)
        access_token = token.get('access_token')
        if not user:
            user = cls.create(authlib_user.id, authlib_user.name,
                              authlib_user.email, authlib_user.data,
                              access_token)
        else:
            user.update(name=authlib_user.name, email=authlib_user.email,
                        data=authlib_user.data, access_token=access_token)

        return user

    def granted_to_app(self, app):
        if self.privileged:
            return True
        from citadel.models.app import AppUserRelation
        r = AppUserRelation.query.filter_by(appname=app.name, user_id=self.id).all()
        return bool(r)

    def list_app(self):
        from citadel.models.app import AppUserRelation, App
        if self.privileged:
            return App.get_all()
        rs = AppUserRelation.query.filter_by(user_id=self.id)
        return [App.get_by_name(r.appname) for r in rs]

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs
                if c.key != 'access_token'}

    def elevate_privilege(self):
        self.privileged = 1
        db.session.add(self)
        db.session.commit()
