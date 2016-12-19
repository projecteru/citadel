# coding: utf-8
import itertools
import json
from datetime import timedelta, datetime
from time import sleep

from etcd import EtcdKeyNotFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import ObjectDeletedError

from citadel.ext import etcd, db
from citadel.libs.mimiron import set_mimiron_route, del_mimiron_route
from citadel.libs.utils import logger
from citadel.models.base import BaseModelMixin, PropsMixin, PropsItem
from citadel.network.plugin import get_ips_by_container
from citadel.rpc import core


class Container(BaseModelMixin, PropsMixin):
    __tablename__ = 'container'
    __table_args__ = (
        db.Index('appname_sha', 'appname', 'sha'),
    )

    appname = db.Column(db.CHAR(64), nullable=False)
    sha = db.Column(db.CHAR(64), nullable=False)
    container_id = db.Column(db.CHAR(64), nullable=False, index=True)
    entrypoint = db.Column(db.String(50), nullable=False)
    env = db.Column(db.String(50), nullable=False)
    cpu_quota = db.Column(db.Numeric(12, 3), nullable=False, default=1)
    podname = db.Column(db.String(50), nullable=False)
    nodename = db.Column(db.String(50), nullable=False)

    initialized = PropsItem('initialized', default=0, type=int)
    removing = PropsItem('removing', default=0, type=int)
    networks = PropsItem('networks', default=dict)

    def __str__(self):
        return 'Container(container_id=%s)' % self.container_id

    def get_uuid(self):
        return 'citadel:container:%s' % self.container_id

    @classmethod
    def create(cls, appname, sha, container_id, entrypoint, env, cpu_quota, podname, nodename):
        try:
            c = cls(appname=appname, sha=sha, container_id=container_id,
                    entrypoint=entrypoint, env=env, cpu_quota=cpu_quota,
                    podname=podname, nodename=nodename)
            db.session.add(c)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None

        specs = c.release and c.release.specs
        if specs:
            set_mimiron_route(c.container_id, c.get_node(), specs.permitted_users)

        from citadel.publish import publisher
        publisher.add_container(c)
        return c.inspect()

    @classmethod
    def get_by_container_id(cls, container_id):
        """get by container_id, prefix can be used in container_id"""
        c = cls.query.filter(cls.container_id.like('{}%'.format(container_id))).first()
        if not c:
            return
        return c.inspect()

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

        query_set = cls.query.filter_by(**kwargs)
        if entrypoint:
            query_set = query_set.filter(cls.entrypoint == entrypoint)

        if sha:
            query_set = query_set.filter(cls.sha.like('{}%'.format(sha)))

        res = query_set.order_by(cls.id.desc())
        return [c.inspect() for c in res]

    @classmethod
    def get_by_release(cls, appname, sha, start=0, limit=20):
        """get by release appname and release sha"""
        cs = cls.query.filter(cls.appname == appname, cls.sha.like('{}%'.format(sha))).order_by(cls.id.desc())
        if limit:
            res = cs[start:start + limit]
        else:
            res = cs.all()

        return [c.inspect() for c in res]

    @classmethod
    def get_by_app(cls, appname, start=0, limit=20):
        """get by appname"""
        cs = cls.query.filter_by(appname=appname).order_by(cls.id.desc())
        if limit:
            res = cs[start:start + limit]
        else:
            res = cs.all()

        return [c.inspect() for c in res]

    @classmethod
    def get_by_pod(cls, podname, start=0, limit=20):
        """get by podname"""
        cs = cls.query.filter_by(podname=podname).order_by(cls.id.desc())
        if not limit:
            res = cs.all()
        else:
            res = cs[start:start + limit]

        return [c.inspect() for c in res]

    @classmethod
    def get_by_node(cls, nodename, start=0, limit=20):
        """get by nodename"""
        cs = cls.query.filter_by(nodename=nodename).order_by(cls.id.desc())
        if not limit:
            res = cs.all()
        else:
            res = cs[start:start + limit]

        return [c.inspect() for c in res]

    @classmethod
    def get(cls, id):
        c = super(Container, cls).get(id)
        return c.inspect()

    @classmethod
    def get_all(cls, start=0, limit=20):
        cs = super(Container, cls).get_all(start, limit)
        return [c.inspect() for c in cs]

    @property
    def deploy_options(self):
        networks = self.info.get('NetworkSettings', {}).get('Networks', {})
        release = self.release
        deploy_options = {
            'specs': release.specs_text,
            'appname': self.appname,
            'image': release.image,
            'podname': self.podname,
            'nodename': self.nodename,
            'entrypoint': self.entrypoint,
            'cpu_quota': float(self.cpu_quota),
            'count': 1,
            'memory': self.info['HostConfig']['Memory'],
            'networks': {network_name: '' for network_name in networks},
            'env': self.info['Config']['Env'],
            'raw': release.raw,
        }
        return deploy_options

    @property
    def ident(self):
        return self.name.rsplit('_', 2)[-1]

    @property
    def healthy(self):
        # TODO: hard code, ugly
        agent2_container_path = '/agent2/{}.ricebook.link/containers/{}'.format(self.nodename, self.container_id)
        try:
            res = etcd.read(agent2_container_path)
        except EtcdKeyNotFound:
            return False
        container_info = json.loads(res.value)
        # if missing 'Healthy', considered healthy
        return container_info.get('Healthy', True)

    @property
    def used_mem(self):
        mem = self.info.get('HostConfig', {}).get('Memory', 0)
        return mem

    @property
    def short_id(self):
        return self.container_id[:7]

    @property
    def short_sha(self):
        return self.sha[:7]

    def mark_removing(self):
        from citadel.publish import publisher
        self.removing = 1
        publisher.remove_container(self)

    def mark_initialized(self):
        self.initialized = 1

    def wait_for_erection(self, timeout=timedelta(minutes=5), period=timedelta(seconds=5)):
        if not isinstance(timeout, timedelta):
            timeout = timedelta(seconds=timeout)

        if not isinstance(period, timedelta):
            period = timedelta(seconds=period)

        must_end = datetime.now() + timeout
        while datetime.now() < must_end:
            if self.healthy:
                return True
            sleep(period.seconds)

        return False

    def inspect(self):
        """must be called after get / create"""
        # 太尼玛假了...
        # docker inspect在删除容器的时候可能需要比较长的时间才有响应
        # 也可能响应过后就直接报错了
        # 所以不如正在删除的容器就不要去inspect了
        if self.removing:
            self.name = 'unknown'
            self.info = {'State': {'Status': 'removing'}}
            return self

        c = core.get_container(self.container_id)
        if not c:
            self.name = 'unknown'
            self.info = {}
            return self

        self.name = c.name
        self.info = json.loads(c.info)
        # network settings 需要保存下来
        # 防止 calico 挂了需要恢复的问题
        networks = self.info.get('NetworkSettings', {}).get('Networks', {})
        if networks and not self.networks:
            self.networks = networks

        return self

    def status(self):
        # patch, 暂时docker不返回
        # 我估计也没办法返回这个状态... 删除的时候好像没办法inspect的
        if self.removing:
            return 'InRemoval'
        status = self.info.get('State', {}).get('Status', 'unknown')
        if status == 'running' and not self.healthy:
            return 'sick'
        return status

    def get_ips(self):
        return get_ips_by_container(self)

    def get_backends(self):
        from .app import Release
        ips = self.get_ips()
        release = Release.get_by_app_and_sha(self.appname, self.sha)
        if not release:
            return []

        specs = release.specs
        entrypoint = specs.entrypoints[self.entrypoint]
        ports = entrypoint.ports
        if not ports:
            return []

        ports = [p.port for p in ports]
        return ['%s:%s' % (ip, port) for ip, port in itertools.product(ips, ports)]

    def get_node(self):
        return core.get_node(self.podname, self.nodename)

    def delete(self):
        from citadel.publish import publisher
        publisher.remove_container(self)
        try:
            del_mimiron_route(self.container_id)
            self.destroy_props()
        except ObjectDeletedError:
            logger.warn('Error during deleting: Object %s already deleted', self)
            return None
        return super(Container, self).delete()

    def to_dict(self):
        d = super(Container, self).to_dict()
        d.update({
            'appname': self.appname,
            'sha': self.sha,
            'container_id': self.container_id,
            'entrypoint': self.entrypoint,
            'env': self.env,
            'cpu_quota': self.cpu_quota,
            'podname': self.podname,
            'nodename': self.nodename,
            'name': self.name,
            'info': self.info,
            'backends': self.get_backends(),
            'ips': self.get_ips(),
        })
        return d
