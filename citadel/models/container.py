# coding: utf-8

import json
import itertools
from sqlalchemy.exc import IntegrityError

from citadel.ext import db
from citadel.rpc import core
from citadel.models.base import BaseModelMixin, PropsMixin, PropsItem
from citadel.network.plugin import get_ips_by_container


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

    removing = PropsItem('removing', default=0, type=int)
    networks = PropsItem('networks', default=dict)

    def __repr__(self):
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
            return c.inspect()
        except IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_container_id(cls, container_id):
        """get by container_id, prefix can be used in container_id"""
        c = cls.query.filter(cls.container_id.like('{}%'.format(container_id))).first()
        if not c:
            return
        return c.inspect()

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
    def ident(self):
        return self.name.rsplit('_', 2)[-1]

    @property
    def short_id(self):
        return self.container_id[:7]

    def mark_removing(self):
        self.removing = 1

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
        return self.info.get('State', {}).get('Status', 'unknown')

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

    def delete(self):
        self.destroy_props()
        super(Container, self).delete()

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
