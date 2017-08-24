# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from sqlalchemy import event, DDL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.utils import cached_property

from citadel.config import DEFAULT_ZONE
from citadel.ext import db, gitlab
from citadel.libs.datastructure import SmartStatus
from citadel.libs.utils import logger
from citadel.models.base import BaseModelMixin, PropsItem, ModelDeleteError, PropsMixin, ModelCreateError
from citadel.models.gitlab import get_project_name, get_file_content, get_commit
from citadel.models.loadbalance import ELBRule
from citadel.models.specs import Specs
from citadel.models.user import User


class EnvSet(dict):

    def to_env_vars(self):
        """外部调用需要的['A=1', 'B=var=1']这种格式"""
        return ['%s=%s' % (k, v) for k, v in self.items()]


class App(BaseModelMixin):
    __tablename__ = 'app'
    name = db.Column(db.CHAR(64), nullable=False, unique=True)
    # 形如 git@gitlab.ricebook.net:platform/apollo.git
    git = db.Column(db.String(255), nullable=False)
    tackle_rule = db.Column(db.JSON)
    # {'prod': {'PASSWORD': 'xxx'}, 'test': {'PASSWORD': 'xxx'}}
    env_sets = db.Column(db.JSON)

    def __str__(self):
        return '<{}:{}>'.format(self.name, self.git)

    @classmethod
    def get_or_create(cls, name, git=None, tackle_rule=None):
        app = cls.get_by_name(name)
        if app:
            return app

        tackle_rule = tackle_rule if tackle_rule else {}
        try:
            app = cls(name=name, git=git, tackle_rule=tackle_rule)
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
    def get_by_user(cls, user_id):
        """拿这个user可以有的app, 跟app自己的user_id没关系."""
        names = AppUserRelation.get_appname_by_user_id(user_id)
        return [cls.get_by_name(n) for n in names]

    @classmethod
    def get_apps_with_tackle_rule(cls):
        return cls.query.filter(cls.tackle_rule != {}).all()

    def get_env_sets(self):
        return self.env_sets or {}

    def get_env_set(self, envname):
        env_sets = self.env_sets or {}
        return EnvSet(env_sets.get(envname, {}))

    def add_env_set(self, envname, env_set):
        env_sets = (self.env_sets or {}).copy()
        env_sets[envname] = env_set
        self.env_sets = env_sets
        logger.debug('Set env set %s for %s, full env_sets: %s', envname, self.name, env_sets)
        db.session.add(self)
        db.session.commit()

    def remove_env_set(self, envname):
        env_sets = (self.env_sets or {}).copy()
        env = env_sets.pop(envname, None)
        if env:
            self.env_sets = env_sets
            db.session.add(self)
            db.session.commit()

        return bool(env)

    @property
    def project_name(self):
        return get_project_name(self.git)

    @property
    def latest_release(self):
        return Release.query.filter_by(app_id=self.id).order_by(Release.id.desc()).limit(1).first()

    @property
    def entrypoints(self):
        release = self.latest_release
        return release and release.entrypoints

    @property
    def specs(self):
        r = self.latest_release
        return r and r.specs

    @property
    def subscribers(self):
        specs = self.specs
        return specs and specs.subscribers

    @property
    def cronjob_entrypoints(self):
        specs = self.specs
        return tuple(t[1] for t in specs.crontab)

    def get_container_list(self, zone=None):
        from .container import Container
        return Container.get_by(appname=self.name, zone=zone)

    def has_problematic_container(self, zone=None):
        containers = self.get_container_list(zone)
        if not containers or {c.status() for c in containers} == {'running'}:
            return False
        return True

    @property
    def gitlab_project(self):
        gitlab_project_name = get_project_name(self.git)
        return gitlab.projects.get(gitlab_project_name)

    @property
    def app_status_assembler(self):
        return AppStatusAssembler(self.name)

    def update_tackle_rule(self, rule):
        """
        {
            "container_tackle_rule": [
                {
                    "strategy": "respawn",
                    "situations": ["(healthy == 0) * 2m"],
                    "kwargs": {
                        "floor": 2,
                        "celling": 8
                    }
                }
            ]
        }
        """
        if isinstance(rule, str):
            rule = json.loads(rule)

        self.tackle_rule = rule
        db.session.add(self)
        db.session.commit()

    def get_release(self, sha):
        return Release.get_by_app_and_sha(self.name, sha)

    def delete(self):
        appname = self.name
        from .loadbalance import ELBRule
        containers = self.get_container_list(None)
        if containers:
            raise ModelDeleteError('App {} is still running, containers {}, remove them before deleting app'.format(appname, containers))
        # delete all releases
        Release.query.filter_by(app_id=self.id).delete()
        # delete all permissions
        AppUserRelation.query.filter_by(appname=appname).delete()
        # delete all ELB rules
        rules = ELBRule.get_by(appname=appname)
        for rule in rules:
            rule.delete()

        return super(App, self).delete()

    def get_associated_elb_rules(self, zone=DEFAULT_ZONE):
        from citadel.models.loadbalance import ELBRule
        return ELBRule.get_by(appname=self.name, zone=zone)

    def get_permitted_user_ids(self):
        return AppUserRelation.get_user_id_by_appname(self.name)

    def to_dict(self):
        d = super(App, self).to_dict()
        d.update({
            'name': self.name,
            'git': self.git,
        })
        return d


class Release(BaseModelMixin, PropsMixin):
    __tablename__ = 'release'
    __table_args__ = (
        db.UniqueConstraint('app_id', 'sha'),
    )

    sha = db.Column(db.CHAR(64), nullable=False, index=True)
    app_id = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False, default='')

    branch = PropsItem('branch', default='')

    def __str__(self):
        return '<{r.name}:{r.short_sha}>'.format(r=self)

    def get_uuid(self):
        return 'citadel:release:%s' % self.id

    @classmethod
    def create(cls, app, sha, branch=None):
        """app must be an App instance"""
        appname = app.name
        gitlab_project_name = app.project_name
        commit = get_commit(gitlab_project_name, sha)
        if not commit:
            raise ModelCreateError('Cannot find gitlab commit for {}:{}'.format(gitlab_project_name, sha))

        specs_text = get_file_content(app.project_name, 'app.yaml', sha)
        Specs.validate(specs_text)

        try:
            new_release = cls(sha=commit.id, app_id=app.id)
            db.session.add(new_release)
            db.session.commit()
        except IntegrityError:
            logger.warn('Fail to create Release %s %s, duplicate', appname, sha)
            db.session.rollback()
            return cls.get_by_app_and_sha(appname, sha)

        if branch:
            new_release.branch = branch

        # after the instance is created, manage app permission through combo
        # permitted_users
        permitted_users = set(new_release.get_permitted_users())
        current_permitted_users = set(User.get(id_) for id_ in AppUserRelation.get_user_id_by_appname(appname))
        come = permitted_users - current_permitted_users
        gone = current_permitted_users - permitted_users
        for u in come:
            if not u:
                continue
            logger.debug('Grant %s to app %s', u, appname)
            AppUserRelation.add(appname, u.id)

        for u in gone:
            if not u:
                continue
            logger.debug('Revoke %s to app %s', u, appname)
            AppUserRelation.delete(appname, u.id)

        # create ELB routes, if there's any
        for combo in new_release.specs.combos.values():
            if not combo.elb:
                continue
            for elbname_and_domain in combo.elb:
                elbname, domain = elbname_and_domain.split()
                try:
                    r = ELBRule.create(combo.zone, elbname, domain, appname, entrypoint=combo.entrypoint, podname=combo.podname)
                except ModelCreateError:
                    new_release.delete()
                    raise
                if r:
                    logger.info('Auto create ELBRule %s for app %s', r, appname)

        return new_release

    def delete(self):
        container_list = self.get_container_list()
        if container_list:
            raise ModelDeleteError('Release {} is still running, delete containers {} before deleting this release'.format(self.short_sha, container_list))
        logger.warn('Deleting release %s', self)
        return super(Release, self).delete()

    def get_permitted_users(self):
        usernames = self.specs.permitted_users
        permitted_users = [User.get(u) for u in usernames]
        return permitted_users

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
            return None

        return cls.query.filter(cls.app_id == app.id, cls.sha.like('{}%'.format(sha))).first()

    @property
    def raw(self):
        """if no build clause in app.yaml, this release is considered raw"""
        return not self.specs.build

    @cached_property
    def short_sha(self):
        return self.sha[:7]

    @cached_property
    def app(self):
        return App.get(self.app_id)

    @property
    def name(self):
        return self.app.name

    def get_container_list(self, zone=None):
        from .container import Container
        return Container.get_by(appname=self.name, sha=self.sha, zone=zone)

    @property
    def gitlab_commit(self):
        commit = get_commit(self.app.project_name, self.sha)
        return commit

    @property
    def commit_message(self):
        if self.gitlab_commit:
            return self.gitlab_commit.message
        return 'commit not found'

    @property
    def author(self):
        if self.gitlab_commit:
            return self.gitlab_commit.author_name
        return 'commit not found'

    @property
    def specs_text(self):
        specs_text = get_file_content(self.app.project_name, 'app.yaml', self.sha)
        return specs_text

    @property
    def specs(self):
        """load app.yaml from GitLab"""
        specs_text = self.specs_text
        return specs_text and Specs.from_string(specs_text) or None

    @property
    def combos(self):
        return self.specs and self.specs.combos

    def describe_entrypoint_image(self, entrypoint_name):
        if not self.specs:
            return self.image, self.raw
        image = self.specs.entrypoints[entrypoint_name].image
        if image:
            return image, True
        return self.image, self.raw

    @property
    def entrypoints(self):
        if not self.specs:
            return {}
        return self.specs.entrypoints

    @property
    def smooth_upgrade(self):
        return self.specs.smooth_upgrade

    @property
    def erection_timeout(self):
        return self.specs.erection_timeout

    def update_image(self, image):
        try:
            self.image = image
            logger.debug('Set image %s for release %s', image, self.sha)
            db.session.add(self)
            db.session.commit()
        except StaleDataError:
            db.session.rollback()

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
    def get_user_id_by_appname(cls, appname):
        rs = cls.query.filter_by(appname=appname).all()
        return [r.user_id for r in rs]

    @classmethod
    def get_appname_by_user_id(cls, user_id):
        rs = cls.query.filter_by(user_id=user_id).all()
        return [r.appname for r in rs]

    @classmethod
    def user_permitted_to_app(cls, user_id, appname):
        user = User.get(user_id)
        if user.privilege:
            return True
        return bool(cls.query.filter_by(user_id=user_id, appname=appname).first())


class AppStatusAssembler:

    """
    a class that contains app status and its container status
    """

    def __init__(self, appname, consult=('citadel', )):
        """
        appname -- citadel app name
        consult -- str, a tuple of data source to use, choose from ('citadel', 'graphite')
        """
        self.app = App.get_by_name(appname)
        self._container_status_map = defaultdict(SmartStatus)
        self._app_status = SmartStatus(name=appname)
        if 'citadel' in consult:
            self.load_citadel_data()

        if 'graphite' in consult:
            self.load_graphite_data()

    @property
    def app_status(self):
        return self._app_status

    @property
    def container_status(self):
        return self._container_status_map.values()

    def load_graphite_data(self):
        raise NotImplementedError

    def load_citadel_data(self):
        container_list = self.app.get_container_list()
        for c in container_list:
            cid = c.short_id
            this_container_status = self._container_status_map[cid]
            this_container_status.name = cid
            this_container_status.status_dic.update({
                'healthy': int(c.healthy),
            })


event.listen(
    App.__table__,
    'after_create',
    DDL('ALTER TABLE %(table)s AUTO_INCREMENT = 10001;'),
)
