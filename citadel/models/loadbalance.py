# -*- coding: utf-8 -*-
import json
from collections import Iterable

import enum
from erulbpy import ELBClient
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import cached_property

from citadel.config import ELB_BACKEND_NAME_DELIMITER, ZONE_CONFIG
from citadel.ext import db, rds
from citadel.libs.datastructure import purge_none_val_from_dict
from citadel.libs.utils import logger, make_unicode, memoize
from citadel.models.base import BaseModelMixin, ModelCreateError
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

    # 如果容器在特殊状态，一律不挂载到 ELB 上
    containers = [c for c in Container.get_by(appname=appname,
                                              entrypoint=entrypoint,
                                              podname=podname,
                                              sha=short_sha)
                  if c not in exclude_containers and
                  not c.override_status]
    return [b for c in containers for b in c.get_backends()]


@memoize
def get_elb_client(name, zone):
    elb_instances = ELBInstance.get_by(name=name, zone=zone)
    elb_urls = [e.addr for e in elb_instances]
    elb_db = ZONE_CONFIG[zone]['ELB_DB']
    return ELBClient(name=name, redis_url=elb_db, elb_urls=elb_urls)


class ELBRule(BaseModelMixin):

    """
    ELB上所有的domain，每个domain会对应相应的rule
    """

    __tablename__ = 'elb_rule'
    __table_args__ = (
        db.UniqueConstraint('elbname', 'domain'),
    )

    zone = db.Column(db.String(50), nullable=False)
    elbname = db.Column(db.String(64), nullable=False)
    domain = db.Column(db.String(128), nullable=False)
    appname = db.Column(db.CHAR(64), nullable=False)
    sha = db.Column(db.CHAR(64), nullable=True, default='')
    rule = db.Column(db.JSON, default={})

    def __str__(self):
        return '<ELBRule: elbname: %s, domain: %s, appname: %s, sha: %s, rule: %s>' % (self.elbname, self.domain, self.appname, self.sha, self.rule)

    @staticmethod
    def validate_rule(rule):
        # TODO
        pass

    @property
    def elb(self):
        return get_elb_client(self.elbname, self.zone)

    @classmethod
    def create(cls, zone, elbname, domain, appname, rule=None, sha='', entrypoint=None, podname=None):
        rule = rule or cls.generate_simple_rule(appname, entrypoint, podname)
        if not rule:
            raise ModelCreateError('Bad rule')
        if not ELBInstance.get_by(name=elbname, zone=zone):
            raise ModelCreateError('No ELB instances found for zone {}, name {}'.format(zone, elbname))

        try:
            r = cls(zone=zone, elbname=elbname, domain=domain, appname=appname, rule=rule, sha=sha)
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
    def get_by(cls, **kwargs):
        return cls.query.filter_by(**purge_none_val_from_dict(kwargs)).order_by(cls.id.desc()).all()

    def delete(self):
        domain = self.domain
        self.elb.delete_rule(domain)
        super(ELBRule, self).delete()
        return True

    @property
    def backends(self):
        return self.rule['backends']

    @property
    def app(self):
        from .app import App
        return App.get_by_name(self.appname)

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
    zone = db.Column(db.String(50), nullable=False)

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
        container = Container.get_by_container_id(container_id)
        b = cls(addr=addr,
                container_id=container_id,
                zone=container.zone,
                name=name)
        db.session.add(b)
        db.session.commit()
        b.comment = comment
        return b

    def is_only_instance(self):
        cls = self.__class__
        elbname = self.name
        remaining_instances = [b for b in cls.get_by(name=elbname) if b.id != self.id]
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
    def get_by(cls, **kwargs):
        container_id = kwargs.pop('container_id', None)
        query_set = cls.query.filter_by(**purge_none_val_from_dict(kwargs))
        if container_id:
            query_set = query_set.filter(cls.container_id.like('{}%'.format(container_id)))

        res = query_set.order_by(cls.id.desc()).all()
        return res

    @cached_property
    def elb(self):
        return get_elb_client(self.name, self.zone)

    @property
    def container(self):
        return Container.get_by_container_id(self.container_id)

    @property
    def ip(self):
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

        elb_rules = ELBRule.get_by(appname=this_batch_containers[0].appname)
        for r in elb_rules:
            for backend_name in r.rule['backends']:
                backends = get_backends(backend_name, exclude_containers=exclude)
                r.elb.set_upstream(backend_name, backends)
