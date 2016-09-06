# -*- coding: utf-8 -*-
from sqlalchemy import event, DDL
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import cached_property

from citadel.ext import db
from citadel.libs.utils import log
from citadel.models.base import BaseModelMixin
from citadel.models.gitlab import get_project_name, get_file_content, get_commit
from citadel.models.specs import Specs


COMBO_MUST_HAVE_FIELD = ('podname', 'entrypoint')
DEFAULT_COMBO = {
    'cpu': 0,
    'memory': 0,
    'count': 1,
    'envs': '',
    'raw': False,
}


class App(BaseModelMixin):
    __tablename__ = 'app'
    name = db.Column(db.CHAR(64), nullable=False, unique=True)
    # 这货就是 git@gitlab.ricebook.net...
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
    def get_by_user(cls, user_id, start=0, limit=20):
        """拿这个user可以有的app, 跟app自己的user_id没关系."""
        names = AppUserRelation.get_appname_by_user_id(user_id, start, limit)
        return [cls.get_by_name(n) for n in names]

    @property
    def uid(self):
        """用来修正app的uid, 默认使用id"""
        return self.user_id or self.id

    @property
    def project_name(self):
        return get_project_name(self.git)

    def get_online_entrypoints(self):
        from .container import Container
        containers = Container.get_by_app(self.name, limit=100)
        return list(set([c.entrypoint for c in containers]))

    def get_online_pods(self):
        from .container import Container
        containers = Container.get_by_app(self.name, limit=100)
        return list(set([c.podname for c in containers]))

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
            log.warn('error getting commit %s %s', app, sha)
            return None

        specs_text = get_file_content(app.project_name, 'app.yaml', sha)
        log.debug('got specs:\n%s', specs_text)
        if not specs_text:
            log.warn('empty specs %s %s', app.name, sha)
            return None

        try:
            r = cls(sha=commit.id, app_id=app.id)
            db.session.add(r)
            db.session.commit()
            return r
        except IntegrityError:
            log.warn('fail to create Release %s %s, duplicate', app.name, sha)
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
    def name(self):
        return self.app and self.app.name or ''

    @cached_property
    def specs(self):
        """load app.yaml from GitLab"""
        specs_text = get_file_content(self.app.project_name, 'app.yaml', self.sha)
        return specs_text and Specs.from_string(specs_text) or None

    def get_combos(self):
        return self.specs.combos

    def update_image(self, image):
        self.image = image
        log.debug('set image %s for release %s', image, self.sha)
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


class AppUserRelation(BaseModelMixin):
    __tablename__ = 'app_user_relation'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'appname'),
    )

    appname = db.Column(db.String(255), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False)

    @classmethod
    def add(cls, appname, user_id):
        try:
            m = cls(appname=appname, user_id=user_id)
            db.session.add(m)
            db.session.commit()
            return m
        except IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def delete(cls, appname, user_id):
        cls.query.filter_by(user_id=user_id, appname=appname).delete()
        db.session.commit()

    @classmethod
    def get_user_id_by_appname(cls, appname, start=0, limit=20):
        rs = cls.query.filter_by(appname=appname)
        return [r.user_id for r in rs[start:start + limit] if r]

    @classmethod
    def get_appname_by_user_id(cls, user_id, start=0, limit=20):
        rs = cls.query.filter_by(user_id=user_id)
        if limit:
            res = rs[start:start + limit]
        else:
            res = rs.all()

        return [r.appname for r in res if r]


event.listen(
    App.__table__,
    "after_create",
    DDL("ALTER TABLE %(table)s AUTO_INCREMENT = 10001;")
)
