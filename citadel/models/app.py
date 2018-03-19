# -*- coding: utf-8 -*-

import json
import yaml
from collections import defaultdict
from marshmallow import ValidationError
from sqlalchemy import event, DDL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.utils import cached_property

from citadel.config import DEFAULT_ZONE
from citadel.ext import db
from citadel.libs.datastructure import SmartStatus
from citadel.libs.exceptions import ModelDeleteError
from citadel.libs.utils import logger
from citadel.models.base import BaseModelMixin
from citadel.models.specs import specs_schema
from citadel.rpc import core_pb2 as pb


class EnvSet(dict):

    reserved_keys = frozenset({
        'ERU_POD',
        'ERU_NODE_IP',
        'ERU_NODE_NAME',
        'ERU_CONTAINER_NO',
        'ERU_MEMORY',
    })

    def __init__(self, *args, **kwargs):
        illegal_keys = self.reserved_keys.intersection(set(kwargs))
        if illegal_keys:
            raise ValueError('Cannot add these keys as app env: {}'.format(illegal_keys))
        return super(EnvSet, self).__init__(*args, **kwargs)

    def to_env_vars(self):
        return ['%s=%s' % (k, v) for k, v in self.items()]


class App(BaseModelMixin):
    name = db.Column(db.CHAR(64), nullable=False, unique=True)
    # 形如 git@gitlab.ricebook.net:platform/apollo.git
    git = db.Column(db.String(255), nullable=False)
    tackle_rule = db.Column(db.JSON)
    # {'prod': {'PASSWORD': 'xxx'}, 'test': {'PASSWORD': 'xxx'}}
    env_sets = db.Column(db.JSON, default={})

    def __str__(self):
        return '<{}:{}>'.format(self.name, self.git)

    @classmethod
    def get_or_create(cls, name, git=None, tackle_rule=None):
        app = cls.get_by_name(name)
        if app:
            return app

        tackle_rule = tackle_rule if tackle_rule else {}
        app = cls(name=name, git=git, tackle_rule=tackle_rule)
        db.session.add(app)
        db.session.commit()
        return app

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

    def get_combos(self):
        return Combo.query.filter_by(appname=self.name).all()

    def create_combo(self, **kwargs):
        kwargs['appname'] = self.name
        return Combo.create(**kwargs)

    def get_combo(self, combo_name):
        return Combo.query.filter_by(appname=self.name, name=combo_name).first()

    def delete_combo(self, combo_name):
        return Combo.query.filter_by(appname=self.name, name=combo_name).delete()

    def grant_user(self, user):
        AppUserRelation.create(self, user)

    def revoke_user(self, user):
        AppUserRelation.query.filter_by(appname=self.name, user_id=user.id).delete()
        db.session.commit()

    def list_users(self):
        from citadel.models.user import User
        user_ids = [r.user_id for r in
                    AppUserRelation.filter_by(appname=self.name).all()]
        users = [User.get(id_) for id_ in user_ids]
        return users

    def get_env_sets(self):
        return self.env_sets

    def get_env_set(self, envname):
        env_sets = self.env_sets
        return EnvSet(env_sets.get(envname, {}))

    def add_env_set(self, envname, data):
        if envname in self.env_sets:
            raise ValueError('{} already exists, use update API'.format(envname))
        self.update_env_set(envname, data)

    def update_env_set(self, envname, data):
        env_set = EnvSet(**data)
        env_sets = self.env_sets.copy()
        env_sets[envname] = env_set
        self.env_sets = env_sets
        logger.debug('Update env set %s for %s, full env_sets: %s', envname, self.name, env_sets)
        db.session.add(self)
        db.session.commit()

    def remove_env_set(self, envname):
        env_sets = self.env_sets.copy()
        env = env_sets.pop(envname, None)
        if env:
            self.env_sets = env_sets
            db.session.add(self)
            db.session.commit()

        return bool(env)

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
        # FIXME
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
        containers = self.get_container_list(None)
        if containers:
            raise ModelDeleteError('App {} is still running, containers {}, remove them before deleting app'.format(appname, containers))
        # delete all releases
        Release.query.filter_by(app_id=self.id).delete()
        # delete all permissions
        AppUserRelation.query.filter_by(appname=appname).delete()
        # TODO: delete all ELB rules
        return super(App, self).delete()

    def get_associated_elb_rules(self, zone=DEFAULT_ZONE):
        # TODO
        pass


class Release(BaseModelMixin):
    __table_args__ = (
        db.UniqueConstraint('app_id', 'sha'),
    )

    sha = db.Column(db.CHAR(64), nullable=False, index=True)
    app_id = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=False, default='')
    specs_text = db.Column(db.JSON)
    # store trivial info like branch, author, git tag, commit messages
    misc = db.Column(db.JSON)

    def __str__(self):
        return '<{r.appname}:{r.short_sha}>'.format(r=self)

    @classmethod
    def create(cls, app, sha, specs_text=None, branch='', git_tag='', author='', commit_message='', git=''):
        """app must be an App instance"""
        appname = app.name

        unmarshal_result = specs_schema.load(yaml.load(specs_text))
        misc = {
            'git_tag': git_tag,
            'author': author,
            'commit_message': commit_message,
        }

        try:
            new_release = cls(sha=sha, app_id=app.id, specs_text=specs_text, misc=misc)
            db.session.add(new_release)
            db.session.commit()
        except IntegrityError:
            logger.warn('Fail to create Release %s %s, duplicate', appname, sha)
            db.session.rollback()
            raise

        return new_release

    def delete(self):
        container_list = self.get_container_list()
        if container_list:
            raise ModelDeleteError('Release {} is still running, delete containers {} before deleting this release'.format(self.short_sha, container_list))
        logger.warn('Deleting release %s', self)
        return super(Release, self).delete()

    @classmethod
    def get(cls, id):
        r = super(Release, cls).get(id)
        # 要检查下 app 还在不在, 不在就失败吧
        if r and r.app:
            return r
        return None

    @classmethod
    def get_by_app(cls, name, start=0, limit=None):
        app = App.get_by_name(name)
        if not app:
            return []

        q = cls.query.filter_by(app_id=app.id).order_by(cls.id.desc())
        return q[start:start + limit]

    @classmethod
    def get_by_app_and_sha(cls, name, sha):
        app = App.get_by_name(name)
        if not app:
            raise ValueError('app {} not found'.format(name))

        if len(sha) < 7:
            raise ValueError('minimum sha length is 7')
        return cls.query.filter(cls.app_id==app.id, cls.sha.like('{}%'.format(sha))).first()

    @property
    def raw(self):
        """if no builds clause in app.yaml, this release is considered raw"""
        return not self.specs.stages

    @property
    def short_sha(self):
        return self.sha[:7]

    @property
    def app(self):
        return App.get(self.app_id)

    @property
    def appname(self):
        return self.app.name

    def get_container_list(self, zone=None):
        from .container import Container
        return Container.get_by(appname=self.appname, sha=self.sha, zone=zone)

    @property
    def git_tag(self):
        return self.misc.get('git_tag')

    @property
    def commit_message(self):
        return self.misc.get('commit_message')

    @property
    def author(self):
        return self.misc.get('author')

    @property
    def git(self):
        return self.misc.get('git')

    @cached_property
    def specs(self):
        dic = yaml.load(self.specs_text)
        unmarshal_result = specs_schema.load(dic)
        return unmarshal_result.data

    @property
    def entrypoints(self):
        return self.specs.entrypoints

    def update_image(self, image):
        try:
            self.image = image
            logger.debug('Set image %s for release %s', image, self.sha)
            db.session.add(self)
            db.session.commit()
        except StaleDataError:
            db.session.rollback()

    def make_core_deploy_options(self, combo_name):
        combo = Combo.query.filter_by(appname=self.appname, name=combo_name).first()
        entrypoint_name = combo.entrypoint_name
        specs = self.specs
        entrypoint = specs.entrypoints[entrypoint_name]
        # TODO: extra hosts support
        # TODO: wtf is meta
        # TODO: wtf is nodelabels
        hook = entrypoint.hook
        if hook:
            hook_opt = pb.HookOptions(after_start=hook.after_start,
                                      before_stop=hook.before_stop,
                                      force=hook.force)
        else:
            hook_opt = None

        healthcheck = entrypoint.healthcheck
        healthcheck_opt = pb.HealthCheckOptions(tcp_ports=[str(p) for p in healthcheck.tcp_ports],
                                                http_port=str(healthcheck.http_port),
                                                url=healthcheck.http_url,
                                                code=healthcheck.http_code)
        entrypoint_opt = pb.EntrypointOptions(name=entrypoint_name,
                                              command=entrypoint.command,
                                              privileged=entrypoint.privileged,
                                              dir=entrypoint.working_dir,
                                              log_config=entrypoint.log_config,
                                              publish=entrypoint.publish,
                                              healthcheck=healthcheck_opt,
                                              hook=hook_opt,
                                              restart_policy=entrypoint.restart)
        app = self.app
        env_set = app.get_env_set(combo.envname)
        networks = {network_name: '' for network_name in combo.networks}
        deploy_opt = pb.DeployOptions(name=specs.name,
                                      entrypoint=entrypoint_opt,
                                      podname=combo.podname,
                                      nodename=combo.nodename,
                                      image=self.image,
                                      extra_args=combo.extra_args,
                                      cpu_quota=combo.cpu_quota,
                                      memory=combo.memory,
                                      count=combo.count,
                                      env=env_set.to_env_vars(),
                                      dns=specs.dns,
                                      extra_hosts=specs.hosts,
                                      volumes=specs.volumes,
                                      networks=networks,
                                      networkmode=entrypoint.network_mode,
                                      user=specs.container_user,
                                      debug=combo.debug)
        return deploy_opt

    def make_core_build_options(self):
        specs = self.specs
        app = self.app
        builds_map = {stage_name: pb.Build(**build) for stage_name, build in specs.builds.items()}
        core_builds = pb.Builds(stages=specs.stages, builds=builds_map)
        container_user = specs.container_user if self.raw else app.name
        opts = pb.BuildImageOptions(name=app.name,
                                    user=container_user,
                                    uid=app.id,
                                    tag=self.short_sha,
                                    builds=core_builds)
        return opts


class Combo(BaseModelMixin):
    __table_args__ = (
        db.UniqueConstraint('appname', 'name'),
    )

    appname = db.Column(db.CHAR(64), nullable=False, index=True)
    name = db.Column(db.CHAR(64), nullable=False, index=True)
    entrypoint_name = db.Column(db.CHAR(64), nullable=False)
    podname = db.Column(db.CHAR(64), nullable=False)
    nodename = db.Column(db.CHAR(64))
    extra_args = db.Column(db.String(100))
    networks = db.Column(db.JSON)  # List of network names
    cpu_quota = db.Column(db.Float, nullable=False)
    memory = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, default=1)
    envname = db.Column(db.CHAR(64))
    debug = db.Column(db.Integer, default=0)

    def __str__(self):
        return '<{} combo:{}>'.format(self.appname, self.name)

    @classmethod
    def create(cls, appname=None, name=None, entrypoint_name=None,
               podname=None, nodename=None, extra_args=None, networks=None,
               cpu_quota=None, memory=None, count=None, envname=None,
               debug=None):
        try:
            combo = cls(appname=appname, name=name,
                        entrypoint_name=entrypoint_name, podname=podname,
                        nodename=nodename, extra_args=extra_args,
                        networks=networks, cpu_quota=cpu_quota, memory=memory,
                        count=count, envname=envname, debug=debug)
            db.session.add(combo)
            db.session.commit()
            return combo
        except IntegrityError:
            db.session.rollback()
            raise


class AppUserRelation(BaseModelMixin):
    __table_args__ = (
        db.UniqueConstraint('user_id', 'appname'),
    )

    appname = db.Column(db.CHAR(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False)

    @classmethod
    def create(cls, app, user):
        relation = cls(appname=app.name, user_id=user.id)
        try:
            db.session.add(relation)
            db.session.commit()
            return relation
        except IntegrityError:
            db.session.rollback()
            raise


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
                'healthy': int(c.is_healthy()),
            })


event.listen(
    App.__table__,
    'after_create',
    DDL('ALTER TABLE %(table)s AUTO_INCREMENT = 10001;'),
)
