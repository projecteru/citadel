# -*- coding: utf-8 -*-
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import cached_property

from citadel.ext import db
from citadel.models.base import BaseModelMixin
from citadel.models.gitlab import get_project_name, get_file_content, get_commit
from citadel.models.specs import Specs


class App(BaseModelMixin):
    __tablename__ = 'app'
    name = db.Column(db.CHAR(64), nullable=False, unique=True)
    git = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, nullable=False, default=0)

    @classmethod
    def get_or_create(cls, name, git):
        app = cls.get_by_name(name)
        if app:
            return app

        try:
            app = cls(name=name, git=git)
            db.session.add(app)
            db.session.commit()
            return app
        except IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get(cls, name=None, user_id=None):
        raise NotImplementedError

    @classmethod
    def get_by_user(cls, user_id):
        raise NotImplementedError

    @property
    def uid(self):
        """用来修正app的uid, 默认使用id
        TODO: dirty?"""
        return self.user_id or self.id

    @property
    def project_name(self):
        return get_project_name(self.git)

    def to_dict(self):
        d = super(App, self).to_dict()
        d.update({
            'name': self.name,
            'git': self.git,
            'uid': self.uid,
        })
        return d


class Release(BaseModelMixin):
    __tablename__ = 'release'
    __table_args__ = (
        db.UniqueConstraint('app_id', 'sha'),
    )

    sha = db.Column(db.CHAR(64), nullable=False, index=True)
    app_id = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False, default='')

    @classmethod
    def create(cls, app, sha):
        """app must be an App instance"""
        commit = get_commit(app.project_name, sha)
        if not commit:
            return None

        content = get_file_content(app.project_name, 'app.yaml', sha)
        if not content:
            return None

        try:
            r = cls(sha=commit.id, app_id=app.id)
            db.session.add(r)
            db.session.commit()
            return r
        except IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get(cls, id):
        r = super(Release, cls).get(id)
        # 要检查下 app 还在不在, 不在就失败吧
        if r and r.app:
            return r
        return None

    @classmethod
    def get_by_app(cls, name, start=0, limit=20):
        app = App.get_by_name(name)
        if not app:
            return []

        q = cls.query.filter_by(app_id=app.id).order_by(cls.id.desc())
        return q[start:start + limit]

    @classmethod
    def get_by_app_and_sha(cls, name, sha):
        app = App.get_by_name(name)
        if not app:
            return

        return cls.query.filter(cls.app_id == app.id, cls.sha.like('{}%'.format(sha))).first()

    @cached_property
    def short_sha(self):
        return self.sha[:7]

    @cached_property
    def app(self):
        return App.get(self.app_id)

    @cached_property
    def specs(self):
        """load app.yaml from GitLab"""
        content = get_file_content(self.app.project_name, 'app.yaml', self.sha)
        return content and Specs.from_string(content) or None

    def update_image(self, image):
        self.image = image
        db.session.add(self)
        db.session.commit()

    def to_dict(self):
        d = super(Release, self).to_dict()
        d.update({
            'app_id': self.app_id,
            'sha': self.sha,
            'image': self.image,
            'specs': self.specs,
        })
        return d
