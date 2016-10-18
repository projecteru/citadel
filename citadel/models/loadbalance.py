# coding: utf-8
import json
from collections import Iterable

import enum
import requests
from requests.exceptions import ReadTimeout, ConnectionError
from sqlalchemy.exc import IntegrityError

from citadel.config import ELB_BACKEND_NAME_DELIMITER
from citadel.ext import db, rds
from citadel.libs.json import Jsonized
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

    def get_lb_clients(self):
        elb_instances = ELBInstance.get_by_name(self.elbname)
        return [elb.lb_client for elb in elb_instances]

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

        if not r.write_rules():
            logger.error('Urite rules to elb failed, no ELB or dead ELB')
            r.delete()
            return None

        # now that the rule has been created, refresh the relevant
        # backend_names in the associating ELB instances
        backends = rule['backends']
        lb_clients = r.get_lb_clients()
        for backend_name in backends:
            for elb in lb_clients:
                elb.refresh_backend(backend_name)

        return r

    @staticmethod
    def generate_simple_rule(appname, entrypoint, podname):
        if not all([appname, entrypoint, podname]):
            logger.warn('cannot generate default rule, missing [appname, entrypoint, podname], got %s', [appname, entrypoint, podname])
            return None
        backend_name = ELB_BACKEND_NAME_DELIMITER.join([appname, entrypoint, podname])
        rule = {
            'default': 'rule0',
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
        lb_clients = self.get_lb_clients()
        for elb in lb_clients:
            if not elb.update_rule(self.domain, self.rule):
                return False

        return True

    def edit_rule(self, rule):
        if not isinstance(rule, dict):
            rule = json.loads(rule)

        self.rule = rule
        db.session.add(self)
        db.session.commit()
        return self.write_rules(rule)

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
        lb_clients = self.get_lb_clients()
        domain = self.domain
        for elb in lb_clients:
            if not elb.delete_rule(domain):
                logger.warn('delete rule from ELB instance %s failed', elb.addr)

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
        addr = self.addr
        rules = ELBRule.query.filter_by(elbname=elbname)
        domains = [r.domain for r in rules]
        # if rules were removed from elb instances, we can safely
        # remove them from citadel as well
        if self.lb_client.delete_rule(domains):
            rules.delete()
            return True
        else:
            logger.warn('Remove rule %s from ELB instance %s failed', domains, addr)
            return False

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).order_by(cls.id.desc()).all()

    @classmethod
    def get_by_container_id(cls, container_id):
        return cls.query.filter(cls.container_id.like('{}%'.format(container_id))).first()

    @property
    def lb_client(self):
        return LBClient(self.addr)

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

    def to_dict(self):
        d = {}
        d['lb_client'] = self.lb_client.to_dict()
        d['name'] = self.name
        return d


class LBClient(Jsonized):

    success_codes = {200, 201}

    def __init__(self, addr):
        if not addr.startswith('http://'):
            addr = 'http://%s' % addr
        self.addr = addr
        self.domain_addr = '%s/__erulb__/domain' % addr
        self.upstream_addr = '%s/__erulb__/upstream' % addr
        self.analysis_addr = '%s/__erulb__/analysis' % addr
        self.rule_addr = '%s/__erulb__/rule' % addr

    def __str__(self):
        return '<ELB client: {}>'.format(self.addr)

    def __hash__(self):
        return hash((self.__class__, self.addr))

    def request(self, method, url, **kwargs):
        try:
            res = requests.request(method, url, **kwargs)
        except (ReadTimeout, ConnectionError):
            logger.critical('Connection problem with ELB instance %s', self.addr)
            return None

        code = res.status_code
        if code not in self.success_codes:
            logger.warn('lb client %s %s, with payload %s, got %s: %s', method, url, kwargs, code, res.text)
        else:
            return res.json()

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def put(self, url, json):
        return self.request('PUT', url, json=json)

    def delete(self, url, json):
        return self.request('DELETE', url, json=json)

    def get_rule(self):
        return self.get(self.rule_addr)

    def update_rule(self, domain, rule):
        data = {'domain': domain, 'rule': rule}
        return self.put(self.rule_addr, data)

    def delete_rule(self, domains):
        data = {'domains': domains}
        res = self.delete(self.rule_addr, data)
        logger.debug('Delete rule on ELB %s with payload %s, got %s', self, data, res)
        return res

    def get_domain(self):
        return self.get(self.domain_addr)

    def get_upstream(self):
        return self.get(self.upstream_addr)

    def update_upstream(self, backend_name, servers):
        if not servers:
            # if servers is empty, remove the backend instead
            return self.delete_upstream(backend_name)
        data = {'backend': backend_name, 'servers': servers}
        res = self.put(self.upstream_addr, data)
        logger.debug('Update backend_name %s on ELB %s with payload %s, got %s', backend_name, self, data, res)
        return res

    def delete_upstream(self, backend_name):
        data = {'backend': backend_name}
        return self.delete(self.upstream_addr, data)

    def to_dict(self):
        return {'domain_addr': self.domain_addr, 'upstream_addr': self.upstream_addr}

    def refresh_backend(self, backend_name):
        backends = ['server {};'.format(b) for b in get_backends(backend_name)]
        return self.update_upstream(backend_name, backends)


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
    if not containers:
        return

    if action == UpdateELBAction.REMOVE:
        exclude = set(containers)
    else:
        exclude = set()

    elb_rules = ELBRule.get_by_app(containers[0].appname)
    already_dealt_with = set()
    for r in elb_rules:
        associated_lb_clients = r.get_lb_clients()
        for backend_name in r.rule['backends']:
            if backend_name in already_dealt_with:
                continue
            backends = ['server {};'.format(b) for b in get_backends(backend_name, exclude_containers=exclude)]
            for lb in associated_lb_clients:
                lb.update_upstream(backend_name, backends)

            already_dealt_with.add(backend_name)
