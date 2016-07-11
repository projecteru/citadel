# coding: utf-8

import json
from sqlalchemy.exc import IntegrityError

from citadel.ext import db, core
from citadel.models.base import BaseModelMixin


class ContainerInspectError(Exception):
    pass


class Container(BaseModelMixin):
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

    @classmethod
    def get_by_release(cls, appname, sha, start=0, limit=20):
        """get by release appname and release sha"""
        cs = cls.query.filter(cls.appname == appname, cls.sha.like('{}%'.format(sha))).order_by(cls.id.desc())
        return [c.inspect() for c in cs[start:start+limit]]

    @classmethod
    def get_by_app(cls, appname, start=0, limit=20):
        """get by appname"""
        cs = cls.query.filter_by(appname=appname).order_by(cls.id.desc())
        return [c.inspect() for c in cs[start:start+limit]]

    @classmethod
    def get(cls, id):
        c = super(Container, cls).get(id)
        return c.inspect()

    @classmethod
    def get_all(cls, start=0, limit=20):
        cs = super(Container, cls).get_all(start, limit)
        return [c.inspect() for c in cs]

    @classmethod
    def delete_by_container_id(cls, container_id):
        cls.query.filter_by(container_id=container_id).delete()
        db.session.commit()

    def inspect(self):
        """must be called after get / create"""
        cs = core.get_containers([self.container_id])
        if len(cs) != 1:
            raise ContainerInspectError()

        c = cs[0]
        self.name = c.name
        self.info = json.loads(c.info)
        return self

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
        })
        return d
