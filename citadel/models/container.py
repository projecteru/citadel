# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError, ObjectDeletedError
from time import sleep

from citadel.config import CORE_DEPLOY_INFO_PATH
from citadel.ext import db
from citadel.libs.datastructure import purge_none_val_from_dict
from citadel.libs.utils import logger
from citadel.models.base import BaseModelMixin, PropsMixin, PropsItem
from citadel.rpc.client import get_core


class ContainerOverrideStatus:
    NONE = 0
    DEBUG = 1
    REMOVING = 2


class Container(BaseModelMixin, PropsMixin):
    __table_args__ = (
        db.Index('appname_sha', 'appname', 'sha'),
    )

    appname = db.Column(db.CHAR(64), nullable=False)
    sha = db.Column(db.CHAR(64), nullable=False)
    container_id = db.Column(db.CHAR(64), nullable=False, index=True)
    entrypoint = db.Column(db.String(50), nullable=False)
    envname = db.Column(db.String(50))
    cpu_quota = db.Column(db.Numeric(12, 3), nullable=False)
    memory = db.Column(db.BigInteger, nullable=False)
    zone = db.Column(db.String(50), nullable=False)
    podname = db.Column(db.String(50), nullable=False)
    nodename = db.Column(db.String(50), nullable=False)
    deploy_info = db.Column(db.JSON, default={})
    override_status = db.Column(db.Integer, default=ContainerOverrideStatus.NONE, nullable=False)

    initialized = PropsItem('initialized', default=0, type=int)

    def __str__(self):
        return '<{}:{}:{}:{}:{}>'.format(self.zone, self.appname, self.short_sha, self.entrypoint, self.short_id)

    def get_uuid(self):
        return 'citadel:container:%s' % self.container_id

    @classmethod
    def create(cls, appname, sha, container_id, entrypoint, envname, cpu_quota, memory, zone, podname, nodename, override_status=ContainerOverrideStatus.NONE):
        try:
            c = cls(appname=appname, sha=sha, container_id=container_id,
                    entrypoint=entrypoint, envname=envname, cpu_quota=cpu_quota,
                    memory=memory, zone=zone, podname=podname,
                    nodename=nodename, override_status=override_status)
            db.session.add(c)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # TODO: This must not go wrong!
            raise

        return c

    @classmethod
    def get_by_container_id(cls, container_id):
        """get by container_id, prefix can be used in container_id"""
        if len(container_id or '') < 7:
            raise ValueError('Must provide full container ID, got {}'.format(container_id))
        c = cls.query.filter(cls.container_id.like('{}%'.format(container_id))).first()
        return c

    @classmethod
    def get_by_container_ids(cls, container_ids):
        containers = [cls.get_by_container_id(cid) for cid in container_ids]
        return [c for c in containers if c]

    @property
    def core_deploy_key(self):
        return '{prefix}/{c.appname}/{c.entrypoint}/{c.nodename}/{c.container_id}'.format(c=self, prefix=CORE_DEPLOY_INFO_PATH)

    def is_healthy(self):
        return self.deploy_info.get('Healthy')

    @property
    def app(self):
        from .app import App
        return App.get_by_name(self.appname)

    @property
    def release(self):
        from .app import Release
        return Release.get_by_app_and_sha(self.appname, self.sha)

    @classmethod
    def get_by(cls, **kwargs):
        sha = kwargs.pop('sha', None)
        entrypoint = kwargs.pop('entrypoint', None)
        if entrypoint == '_all':
            # all means including all entrypoints
            entrypoint = None

        query_set = cls.query.filter_by(**purge_none_val_from_dict(kwargs))
        if entrypoint:
            query_set = query_set.filter(cls.entrypoint == entrypoint)

        if sha:
            query_set = query_set.filter(cls.sha.like('{}%'.format(sha)))

        res = query_set.order_by(cls.id.desc())
        return res

    @property
    def specs_entrypoint(self):
        return self.release.specs.entrypoints[self.entrypoint]

    @property
    def backup_path(self):
        return self.specs_entrypoint.backup_path

    @property
    def publish(self):
        return self.deploy_info.get('Publish', {})

    @property
    def ident(self):
        return self.name.rsplit('_', 2)[-1]

    @property
    def short_id(self):
        return self.container_id[:7]

    @property
    def short_sha(self):
        return self.sha[:7]

    def is_removing(self):
        return self.override_status == ContainerOverrideStatus.REMOVING

    def is_cronjob(self):
        return self.entrypoint in self.app.cronjob_entrypoints

    def is_debug(self):
        return self.override_status == ContainerOverrideStatus.DEBUG

    def mark_debug(self):
        self.override_status = ContainerOverrideStatus.DEBUG
        try:
            db.session.commit()
        except StaleDataError:
            db.session.rollback()

    def mark_removing(self):
        self.override_status = ContainerOverrideStatus.REMOVING
        try:
            db.session.commit()
        except StaleDataError:
            db.session.rollback()

    def mark_initialized(self):
        self.initialized = 1

    def update_deploy_info(self, deploy_info):
        logger.debug('Update deploy_info for %s: %s', self, deploy_info)
        self.deploy_info = deploy_info
        db.session.add(self)
        db.session.commit()

    def wait_for_erection(self, timeout=timedelta(minutes=5), period=timedelta(seconds=2)):
        """wait until this container is healthy, timeout can be timedelta or
        seconds, if timeout is 0, don't even wait and just report healthy"""
        if not timeout:
            return True
        if not isinstance(timeout, timedelta):
            timeout = timedelta(seconds=timeout)

        if not isinstance(period, timedelta):
            period = timedelta(seconds=period)

        must_end = datetime.now() + timeout
        logger.debug('Waiting for container %s to become healthy...', self)
        while datetime.now() < must_end:
            if self.is_healthy():
                return True
            sleep(period.seconds)
            # deploy_info is written by watch-etcd services, so it's very
            # important to constantly query database, without refresh we'll be
            # constantly hitting sqlalchemy cache
            db.session.refresh(self, attribute_names=['deploy_info'])
            db.session.commit()

        return False

    def status(self):
        if self.is_debug():
            return 'debug'
        if self.is_removing():
            return 'removing'
        running = self.deploy_info.get('Running')
        healthy = self.deploy_info.get('Healthy')
        if running:
            if healthy:
                return 'running'
            else:
                return 'sick'
        else:
            return 'dead'

    def get_node(self):
        return get_core(self.zone).get_node(self.podname, self.nodename)

    def delete(self):
        try:
            self.destroy_props()
            logger.debug('Delete container %s', self)
        except ObjectDeletedError:
            logger.debug('Error during deleting: Object %s already deleted', self)
            return None
        return super(Container, self).delete()

    def to_dict(self):
        d = super(Container, self).to_dict()
        d.update({
            'appname': self.appname,
            'sha': self.sha,
            'container_id': self.container_id,
            'entrypoint': self.entrypoint,
            'envname': self.envname,
            'cpu_quota': self.cpu_quota,
            'zone': self.zone,
            'podname': self.podname,
            'nodename': self.nodename,
            'name': self.name,
            'deploy_info': self.deploy_info,
        })
        return d
