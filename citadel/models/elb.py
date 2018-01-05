# -*- coding: utf-8 -*-

import enum
from collections import Iterable
from sqlalchemy import String, JSON
from sqlalchemy import Column, Index
from werkzeug.utils import cached_property

from elb import ELBSet, RuleSet, UpStream
from elb import UARule, BackendRule, PathRule

from citadel.libs.datastructure import purge_none_val_from_dict
from citadel.libs.utils import logger, memoize
from citadel.libs.jsonutils import Jsonized

from citadel.config import ELB_BACKEND_NAME_DELIMITER
from citadel.models.base import BaseModelMixin
from citadel.models.container import Container


rule_types = {
    'ua': UARule,
    'backend': BackendRule,
    'path': PathRule,
}


def build_elb_rule(rule):
    """rule的结构, args随着type变化.
    {
        "name0": {
            "type": "path",
            "args": {
                "succ": "name1",
                "fail": "name2",
                "pattern": "^test$",
                "regex": "",
                "rewrite": "",
            },
        },
    }
    """
    if len(rule) != 1:
        message = 'Build ELBRule error: bad format %s', rule
        logger.error(message)
        raise ValueError(message)

    name = list(rule.keys())[0]
    rule = list(rule.values())[0]
    if rule.get('type') not in rule_types:
        message = 'Build ELBRule error: bad rule type'
        logger.error(message)
        raise ValueError(message)

    cls = rule_types[rule['type']]
    return cls(name=name, **rule['args'])


def build_elb_ruleset(arguments):
    """把arguments格式的JSON变成一个RuleSet对象, 必须合法才行"""
    init = arguments.get('init')
    rules = arguments.get('rules', [])
    if not (init and rules):
        message = 'Build ELBRuleSet error: init/rules not correct'
        logger.error(message)
        raise ValueError(message)

    rules = [build_elb_rule(r) for r in rules]
    rules = [r for r in rules if r]
    ruleset = RuleSet(init, rules)
    if not ruleset.check_rules():
        message = 'Build ELBRuleSet error: fail to check rules'
        logger.error(message)
        raise ValueError(message)

    return ruleset


@memoize
def get_elb_client(name, zone):
    elb_instances = ELBInstance.query.filter_by(name=name, zone=zone).all()
    elb_urls = [e.addr for e in elb_instances]
    return ELBSet(elb_urls)


class ELBRuleSet(BaseModelMixin, Jsonized):
    """(app, pod, entrypoint)的容器对elbname应用规则,
    规则包括(domain, arguments)"""

    __tablename__ = 'elb_rule_set'
    __table_args__ = (
        Index('idx_app_pod_entry', 'appname', 'podname', 'entrypoint'),
        Index('idx_elb_zone', 'elbname', 'zone'),
    )

    appname = Column(String(100), default='')
    podname = Column(String(100), default='')
    entrypoint = Column(String(100), default='')
    elbname = Column(String(100), default='')
    zone = Column(String(100), default='')
    domain = Column(String(100), default='')
    arguments = Column(JSON)

    @classmethod
    def create(cls, appname, podname, entrypoint,
               elbname, zone, domain, arguments):
        # 检查下这个arguments合法不
        build_elb_ruleset(arguments)
        return super(ELBRuleSet, cls).create(appname=appname, podname=podname,
                entrypoint=entrypoint, elbname=elbname, zone=zone,
                domain=domain, arguments=arguments)

    def to_elbruleset(self):
        return build_elb_ruleset(self.arguments)

    def get_backend_rule(self):
        elbruleset = self.to_elbruleset()
        return [r for r in elbruleset.rules if isinstance(r, BackendRule)]

    def get_elbset(self):
        return get_elb_client(self.elbname, self.zone)


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
    return [b for c in containers for b in c.publish.values()]


class ELBInstance(BaseModelMixin, Jsonized):
    """name 相同的 ELBInstance 组成一个 ELB, ELB 是一个虚拟的概念"""
    __tablename__ = 'elb'
    __table_args__ = (
        Index('idx_container', 'container_id'),
    )

    addr = Column(String(128), nullable=False)
    container_id = Column(String(64), nullable=False)
    name = Column(String(64))
    zone = Column(String(50), nullable=False)

    @classmethod
    def create(cls, addr, container_id, name):
        container = Container.get_by_container_id(container_id)
        ins = super(ELBInstance, cls).create(addr=addr, container_id=container_id,
                zone=container.zone, name=name)
        if not ins:
            return
        return ins

    @classmethod
    def get_by_zone(cls, zone):
        return cls.query.filter_by(zone=zone).order_by(cls.id.desc()).all()

    def is_only_instance(self):
        cls = self.__class__
        elbname = self.name
        remaining_instances = [b for b in cls.get_by(name=elbname) if b.id != self.id]
        return not remaining_instances

    def clear_rules(self):
        """clear rules in the whole ELB"""
        rules = ELBRuleSet.query.filter_by(elbname=self.name).all()
        domains = [r.domain for r in rules]
        for rule in rules:
            elbset = rule.get_elbset()
            elbset.delete_domain_rules(domains)
        for rule in rules:
            rule.delete()

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
    def address(self):
        _, address = self.container.publish.popitem()
        return address

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

        elb_rule_sets = ELBRuleSet.query.filter_by(appname=appname).all()
        for ruleset in elb_rule_sets:
            for backend_rule in ruleset.get_backend_rule():
                backend_name = backend_rule.servername
                backends = get_backends(backend_name, exclude_containers=exclude)
                upstream = UpStream(backend_name, {b: '' for b in backends})

                elbset = get_elb_client(ruleset.elbname, ruleset.zone)
                elbset.set_upstream(upstream)
