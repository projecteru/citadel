# -*- coding: utf-8 -*-

from authlib.client.apps import github

from citadel.config import OAUTH_APP_NAME
from citadel.ext import db, fetch_token
from citadel.models.base import BaseModelMixin


def get_current_user():
    if fetch_token(OAUTH_APP_NAME):
        authlib_user = github.fetch_user()
        return User.from_authlib_user(authlib_user)
    return None


class User(BaseModelMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.CHAR(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    privileged = db.Column(db.Integer, default=0)
    data = db.Column(db.JSON)

    @classmethod
    def create(cls, id, name, email, data=None):
        user = cls(id=id, name=name, email=email, data=data)
        db.session.add(user)
        db.session.commit()
        return user

    def __str__(self):
        return '{class_} {u.id} {u.name}'.format(
            class_=self.__class__,
            u=self,
        )

    @classmethod
    def from_authlib_user(cls, authlib_user):
        user = cls.query.filter_by(id=authlib_user.id).first()
        if not user:
            user = cls.create(authlib_user.id, authlib_user.name,
                              authlib_user.email, authlib_user.data)
        else:
            user.update(name=authlib_user.name, email=authlib_user.email,
                        data=authlib_user.data)

        return user

    def elevate_privilege(self):
        self.privileged = 1
        db.session.add(self)
        db.session.commit()
