# coding: utf-8
import json
from collections import Iterable

import enum
from erulbpy import ELBClient
from sqlalchemy.exc import IntegrityError

from citadel.config import ELB_REDIS_URL, ELB_BACKEND_NAME_DELIMITER
from citadel.ext import db, rds
from citadel.libs.utils import logger, make_unicode
from citadel.models.base import BaseModelMixin, JsonType
from citadel.models.container import Container


"""
配合ELB的部分.
现在ELB实际按照名字来区别, 名字相同的多个ELB实例认为是一个ELB的多个实例.
路由记录挂载在名字上, 也就是说名字相同的一组ELB实例实际上的等价的.
所有对路由记录的操作, 都会反应到对应的所有ELB实例上.
"""


def get_backends(backend_name, exclude_containers=()):
    """get container backends for backend_name"""
    components = backend_name.split(ELB_BACKEND_NAME_DELIMITER)
    if len(components) == 3:
        appname, entrypoint, podname = components
        short_sha = None
    else:
        appname, entrypoint, podname, short_sha = components

    containers = [c for c in Container.get_by(appname=appname,
                                              entrypoint=entrypoint,
                                              podname=podname,
                                              sha=short_sha)
                  if c not in exclude_containers and
                  not c.removing]
    return [b for c in containers for b in c.get_backends()]


class ELBRule(BaseModelMixin):

    """
    ELB上所有的domain，每个domain会对应相应的rule
    """

    __tablename__ = 'elb_rule'
    __table_args__ = (
        db.UniqueConstraint('elbname', 'domain'),
    )

    elbname = db.Column(db.String(64), nullable=False)
    domain = db.Column(db.String(128), nullable=False)
    appname = db.Column(db.CHAR(64), nullable=False)
    sha = db.Column(db.CHAR(64), nullable=True, default='')
    rule = db.Column(JsonType, default={})

    def __str__(self):
        return '<ELBRule: elbname: %s, domain: %s, appname: %s, sha: %s, rule: %s>' % (self.elbname, self.domain, self.appname, self.sha, self.rule)

    @staticmethod
    def validate_rule(rule):
        # TODO
        pass

    @property
    def elb(self):
        return ELBClient(name=self.elbname, redis_url=ELB_REDIS_URL)

    @classmethod
    def create(cls, elbname, domain, appname, rule=None, sha='', entrypoint=None, podname=None):
        rule = rule or cls.generate_simple_rule(appname, entrypoint, podname)
        if not rule:
            return None

        try:
            r = cls(elbname=elbname, domain=domain, appname=appname, rule=rule, sha=sha)
            db.session.add(r)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None

        r.write_rules()
        # now that the rule has been created, refresh the relevant
        # backend_names in the associating ELB instances
        backends = rule['backends']
        for backend_name in backends:
            backends = get_backends(backend_name)
            r.elb.set_upstream(backend_name, backends)

        return r

    @staticmethod
    def generate_simple_rule(appname, entrypoint, podname):
        if not all([appname, entrypoint, podname]):
            logger.warn('cannot generate default rule, missing [appname, entrypoint, podname], got %s', [appname, entrypoint, podname])
            return None
        backend_name = ELB_BACKEND_NAME_DELIMITER.join([appname, entrypoint, podname])
        rule = {
            'default': backend_name,
            'rules_name': ['rule0'],
            'init_rule': 'rule0',
            'backends': [backend_name],
            'rules': {
                'rule0': {'type': 'general', 'conditions': [{'backend': backend_name}]}
            }
        }
        return rule

    def write_rules(self):
        # now that rule was created in citadel, update all associating ELB
        # clients, if any one fails, rollback in citadel
        return self.elb.set_rule(self.domain, self.rule)

    def edit_rule(self, rule):
        if not isinstance(rule, dict):
            rule = json.loads(rule)

        self.rule = rule
        db.session.add(self)
        db.session.commit()
        return self.write_rules()

    @classmethod
    def get_by_app(cls, appname):
        return cls.query.filter_by(appname=appname).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_elb(cls, elbname):
        return cls.query.filter_by(elbname=elbname).order_by(cls.id.desc()).all()

    @classmethod
    def get_by(cls, **kwargs):
        return cls.query.filter_by(**kwargs).order_by(cls.id.desc()).first()

    def delete(self):
        domain = self.domain
        self.elb.delete_rule(domain)
        super(ELBRule, self).delete()
        return True

    @property
    def backends(self):
        return self.rule['backends']

    def to_dict(self):
        return {
            'elbname': self.elbname,
            'domain': self.domain,
        }


class ELBInstance(BaseModelMixin):
    """name 相同的 ELBInstance 组成一个 ELB, ELB 是一个虚拟的概念"""
    __tablename__ = 'elb'

    addr = db.Column(db.String(128), nullable=False)
    container_id = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(64))

    @property
    def comment(self):
        comment = rds.get('citadel:elb:{}:comment'.format(self.name))
        return make_unicode(comment)

    @comment.setter
    def comment(self, val):
        if val:
            rds.set('citadel:elb:{}:comment'.format(self.name), val)

    @classmethod
    def create(cls, addr, container_id, name, comment=''):
        b = cls(addr=addr, container_id=container_id, name=name)
        db.session.add(b)
        db.session.commit()
        b.comment = comment
        return b

    def is_only_instance(self):
        cls = self.__class__
        elbname = self.name
        remaining_instances = [b for b in cls.get_by_name(elbname) if b.id != self.id]
        return not remaining_instances

    def clear_rules(self):
        """clear rules in the whole ELB"""
        elbname = self.name
        rules = ELBRule.query.filter_by(elbname=elbname)
        domains = [r.domain for r in rules]
        # if rules were removed from elb instances, we can safely
        # remove them from citadel as well
        self.elb.delete_rule(domains)
        rules.delete()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_container_id(cls, container_id):
        return cls.query.filter(cls.container_id.like('{}%'.format(container_id))).first()

    @property
    def elb(self):
        return ELBClient(name=self.name, redis_url=ELB_REDIS_URL)

    @property
    def container(self):
        return Container.get_by_container_id(self.container_id)

    @property
    def ip(self):
        """要么是容器的IP, 要么是宿主机的IP, 反正都可以从容器那里拿到."""
        if not self.container:
            return 'Unknown'
        ips = self.container.get_ips()
        return ips and ips[0] or 'Unknown'

    def is_alive(self):
        return self.container and self.container.status() == 'running'


class UpdateELBAction(enum.Enum):
    ADD = 0
    REMOVE = 1


def update_elb_for_containers(containers, action=UpdateELBAction.ADD):
    """看action来决定到底是要怎么搞.
    如果是ADD就很简单, 直接加;
    如果是REMOVE就要剔除这些容器的服务节点, 再更新."""
    if not isinstance(containers, Iterable):
        containers = [containers]

    containers = [c for c in containers if c]
    for appname in set(c.appname for c in containers):
        this_batch_containers = [c for c in containers if c.appname == appname]
        exclude = set()
        if action == UpdateELBAction.REMOVE:
            exclude = set(this_batch_containers)

        elb_rules = ELBRule.get_by_app(this_batch_containers[0].appname)
        for r in elb_rules:
            for backend_name in r.rule['backends']:
                backends = get_backends(backend_name, exclude_containers=exclude)
                r.elb.set_upstream(backend_name, backends)
